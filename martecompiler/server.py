'''
Core definition of the marte-compiler server containing the directory cleaning mechanism,
the FTP host system and the session management REST API endpoints.
'''

import re
import logging
import os
import uuid
import time
import datetime
import pathlib
from subprocess import STDOUT
import subprocess
import shutil
import traceback
import json
import yaml

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.responses import PlainTextResponse, JSONResponse

from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.authorizers import DummyAuthorizer


def log(string):
    ''' Log to screen and to the service journal '''
    logging.info(string)
    print(string)

# Check if the environment variable exists
root_dir = os.environ.get("MARTEC_ROOTDIR", "/opt/martecompiler")

templates = Jinja2Templates(directory=os.path.join(root_dir, 'martecompiler','templates'))

with open(os.path.join(root_dir, 'settings.yml'), 'r', encoding='utf-8') as infile:
    settings = yaml.safe_load(infile)

class Runner(): # pylint: disable=R0903
    ''' Class instance of the runner object which is used to execute compilations '''
    def __init__(self):
        self.job_id = str(uuid.uuid4())
        self.directory = os.path.join(settings['temp_directory'],self.job_id)
        if os.path.exists(self.directory):
            shutil.rmtree(self.directory)
        os.mkdir(self.directory)

    def run(self):
        ''' Execute a compilation '''
        volumes = str(os.path.abspath(self.directory))  + ":/root/compilation"
        cmdline = ["docker","run","-v",volumes,"-w","/root/compilation","sudilav1/martesim:latest",
                "make", "-f", "Makefile.x86-linux"]
        log(f"Running command: {' '.join(cmdline)}")
        with subprocess.Popen(
                ['tee', str(os.path.abspath(os.path.join(self.directory, "output.log")))],
                stdin=subprocess.PIPE
            ) as tee:
            with subprocess.Popen(cmdline, stdout=tee.stdin, stderr=STDOUT) as p:
                p.wait()
        try:
            tee.stdin.close()
        except AttributeError:
            pass

def run_ftp():
    ''' Hosts the FTP Server to allow transferring of files '''
    # get a hash digest from a clear-text password
    # hash = md5('12345').hexdigest()
    authorizer = DummyAuthorizer()
    if not os.path.exists(settings['temp_directory']):
        os.mkdir(settings['temp_directory'])
    authorizer.add_user(settings['username'], settings['password'],
                        settings['temp_directory'], perm='elradfmwMT')
    authorizer.add_anonymous(settings['temp_directory'])
    handler = FTPHandler
    handler.authorizer = authorizer
    # IP set to 0.0.0.0 so it listens on all internet connections
    server = FTPServer(('0.0.0.0', settings['ftp_port']), handler)
    server.serve_forever()

def parse_times(time_string):
    ''' Take a time string and interpret it into it's numeric units '''
    time_string = time_string.lower()
    time_string = time_string.replace(" ", "")
    pattern = re.compile(r'(\d+)\s*(d|day|days|h|hour|hours|m|'
                         r'minute|minutes|s|second|seconds)')

    # Dictionary to hold the value in seconds of each time unit
    time_units = {
        'd': 86400, 'day': 86400, 'days': 86400,
        'h': 3600, 'hour': 3600, 'hours': 3600,
        'm': 60, 'minute': 60, 'minutes': 60,
        's': 1, 'second': 1, 'seconds': 1
    }

    # Find all denominations in the input string
    matches = pattern.findall(time_string)

    # Initialize total seconds
    total_seconds = 0

    # Sum up the total seconds for each match
    for value, unit in matches:
        total_seconds += int(value) * time_units[unit]

    parts = re.split('(\d+)', time_string) # pylint: disable=W1401
    for part in parts:
        if part:
            if not part.isnumeric():
                if part not in time_units:
                    msg = f"{part} is not a recognised string. Could not read config file"
                    raise ValueError(msg)

    return total_seconds

def parse_datasizes(datasize_string):
    ''' Take a string and parse it to interpret the numeric value of file/directory size. '''
    datasize_string = datasize_string.lower()
    datasize_string = datasize_string.replace(" ", "")
    pattern = re.compile(r'(\d+)\s*(b|kb|mb|gb|k|m|g|byte|bytes|kilobyte'
                         r'|kilobytes|megabyte|megabytes|gigabyte|gigabytes)')

    # Dictionary to hold the value in bytes for each data unit
    data_units = {
        'gb': 1000000000, 'g': 1000000000, 'gigabyte': 1000000000, 'gigabytes': 1000000000,
        'mb': 1000000, 'm': 1000000, 'megabyte': 1000000, 'megabytes': 1000000,
        'kb': 1000, 'k': 1000, 'kilobyte': 1000, 'kilobytes': 1000,
        'b': 1, 'byte': 1, 'bytes': 1
    }

    # Find all denominations in the input string
    matches = pattern.findall(datasize_string)

    # Initialize total bytes
    total_bytes = 0

    # Sum up the total bytes for each match
    for value, unit in matches:
        total_bytes += int(value) * data_units[unit]

    parts = re.split('(\d+)', datasize_string) # pylint: disable=W1401
    for part in parts:
        if part:
            if not part.isnumeric():
                if part not in data_units:
                    msg = f"{part} is not a recognised string. Could not read config file"
                    raise ValueError(msg)
    return total_bytes

def delete_generic(file):
    ''' Delete a file/directory '''
    shutil.rmtree(file, ignore_errors=True)
    os.remove(file)

def delete_old(files, keep_for):
    ''' Delete files based on age '''
    for file in files:
        age = time.time() - os.path.getmtime(file)
        if age > keep_for:
            log(f"Deleting {file} because it is {age} seconds old")
            delete_generic(file)

def directory_size(file):
    ''' Get the directory size '''
    size_check = subprocess.run(['du', '-s', file], capture_output=True, text=True, check=False)
    file_size = size_check.stdout.split()[0]
    return int(file_size)

def clean_dir():
    ''' Directory cleaning mechanism, handles to maintain a directory and avoid
    oversize or stale objects. '''
    # Delete anything older than x time, or delete oldest x amount when directory is
    # at size, settings['temp_directory'] being the directory
    settings_file = os.path.join(root_dir,'settings.yml')
    if not os.path.exists(settings['temp_directory']):
        os.mkdir(settings['temp_directory'])

    try:
        period = parse_times(settings['period'])
        hours = str(datetime.timedelta(seconds = period))
        print(f"Running cleanup routine every {hours}")
    except KeyError:
        log(f"Defaulting to running cleanup routine daily. Change in {settings_file}")
        period = 60 * 60 * 24    # 24 hours in seconds

    try:
        keep_for = parse_times(settings['keep_for'])
        hours = str(datetime.timedelta(seconds = keep_for))
        print(f"Deleting files older than {hours}")
    except KeyError:
        log(f"Defaulting to never trimming files. Change in {settings_file}")
        keep_for = -1

    try:
        trim_to = parse_datasizes(settings['trim_to'])
        print(f"Limiting directory size to {trim_to} bytes")
    except KeyError:
        log(f"Defaulting to not limiting max directory size. Change in {settings_file}")
        trim_to = -1

    while True:
        time.sleep(period)
        log("Running cleanup routine...")
        files = list(pathlib.Path(settings['temp_directory']).iterdir())
        if keep_for != -1:
            delete_old(files, keep_for)

        if trim_to != -1:
            file_size = directory_size(settings['temp_directory'])
            while file_size > trim_to:
                log(f"Cleaning {settings['temp_directory']} because it is {file_size}B")
                files = list(pathlib.Path(settings['temp_directory']).iterdir())
                files.sort(key=os.path.getmtime)
                log(f"deleting the oldest file, {files[0]}")
                delete_generic(files[0])
                file_size = directory_size(settings['temp_directory'])

active_runners = {}
running = {}
finished_jobs = {}
failed_jobs = {}

async def homepage(_):
    ''' Endpoint for the index, returns the state of sessions '''
    context = {"active_runners": active_runners,
               "running": running, "finished_jobs": finished_jobs,
               "failed_jobs": failed_jobs}
    return JSONResponse(json.dumps(context, indent=4))

async def start_session(_):
    ''' Start a new session and return it's job index '''
    runner = Runner()
    active_runners[runner.job_id] = runner
    return PlainTextResponse(runner.job_id)

async def error(_):
    """
    An example error. Switch the `debug` setting to see either tracebacks or 500 pages.
    """
    raise RuntimeError("Oh no")

async def not_found(request: Request, _):
    """
    Return an HTTP 404 page.
    """
    template = "404.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context, status_code=404)

async def server_error(request: Request, exc: HTTPException):
    """
    Return an HTTP 500 page.
    """
    template = "500.html"
    context = {"request": request, "exception": exc}
    return templates.TemplateResponse(template, context, status_code=500)

async def run_compile(request):
    ''' Execute a runner given it's session id to compile. '''
    # So we need to collect our info from the request
    session_id = request.query_params['session_id']
    if session_id not in active_runners:
        response = "Failure - Runner session does not exist, run start_session first"
        return PlainTextResponse(response, status_code=500)
    try:
        session_id = request.query_params['session_id']
        runner = active_runners[session_id]
        active_runners.pop(session_id)
        running[session_id] = runner
        runner.run()
        running.pop(session_id)
        finished_jobs[session_id] = runner
        return PlainTextResponse("Success", status_code=200)
    except (KeyError, AttributeError, ValueError, AssertionError) as e:
        try:
            active_runners.pop(session_id)
        except (KeyError, AttributeError, ValueError):
            pass
        try:
            running.pop(session_id)
        except (KeyError, AttributeError, ValueError):
            pass
        traceback.print_exc()
        failed_jobs[session_id] = runner
        return await server_error(request, e)

routes = [
    Route('/', homepage),
    Route('/run_session', run_compile),
    Route('/start_session', start_session)
]

exception_handlers = {
    404: not_found,
    500: server_error
}

app = Starlette(debug=False, routes=routes, exception_handlers=exception_handlers)
