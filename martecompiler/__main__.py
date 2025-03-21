'''
Main entrypoint for the compiler service to start off the threads for the FTP,
the directory cleaner and the REST API endpoints for session management.
'''

import threading
import os
import yaml
from starlette.applications import Starlette
import uvicorn

from martecompiler.server import routes, exception_handlers, run_ftp, clean_dir

# Established our Root Directory from our Environment configuration or go to default
root_dir = os.environ.get("MARTEC_ROOTDIR", "/opt/martecompiler")

# Load out settings
try:
    with open(os.path.join(root_dir,'settings.yml'), 'r', encoding='utf-8') as infile:
        settings = yaml.safe_load(infile)
except FileNotFoundError:
    print("Error: settings.yml file not found.")
except IsADirectoryError:
    print("Error: settings.yml is a directory, not a file.")
except PermissionError:
    print("Error: Permission denied when accessing settings.yml.")
except OSError as e:
    print(f"OS error occurred: {e}")
except yaml.YAMLError as e:
    print(f"YAML syntax error: {e}")
except (UnicodeDecodeError, UnicodeError) as e:
    print(f"Invalid UTF-8 sequences detected in settings file: {e}")

# Start the Starlette app
app = Starlette(debug=True, routes=routes, exception_handlers=exception_handlers)

# Start our FTP and Clean Directory threads
x = threading.Thread(target=run_ftp)
x.start()
x = threading.Thread(target=clean_dir)
x.start()

# Run our Starlette HTTP App
uvicorn.run(app, host='0.0.0.0', port=settings['http_port'],h11_max_incomplete_event_size=16777216)

