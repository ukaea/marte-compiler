import pytest
from starlette.testclient import TestClient
from unittest.mock import patch, MagicMock
from martecompiler.server import app, Runner, log, run_ftp, parse_datasizes, parse_times,delete_generic,delete_old, directory_size
import shutil
import os
import time
import copy
import subprocess
from martecompiler import server
import martecompiler
from unittest import mock

root_dir = os.environ.get("MARTEC_ROOTDIR", "/opt/martecompiler")

client = TestClient(app)

# --- Tests for Routes ---

def test_homepage():
    response = client.get("/")
    assert response.status_code == 200
    assert "active_runners" in response.json()

@patch("martecompiler.server.Runner.run", MagicMock())
def test_start_session():
    response = client.get("/start_session")
    assert response.status_code == 200
    assert response.text  # Job ID should be returned

def test_run_test_no_session():
    response = client.get("/run_session?session_id=nonexistent")
    assert response.status_code == 500
    assert "Failure - Runner session does not exist" in response.text

@patch("martecompiler.server.active_runners", new_callable=dict)
def test_run_test_success(mock_active_runners, monkeypatch):
    # Mock a Runner session in active_runners
    def mock_popen(cmd, *args, **kwargs):
        # Assume the command has source and destination paths
        source = os.path.join(os.path.dirname(__file__), 'results.csv')
        dest = os.path.join('/home','martecompiler',runner.job_id,'output.csv')
        #shutil.copy(source, dest)  # Perform the file copy
        class MockProcess:
            class stdin:
                def close(*args):
                    pass
            def __init__(self, *args, **kwargs):
                self.stdin = self.stdin()
            def communicate(self):
                return b"success", b""  # Mock stdout, stderr
            def wait(self):
                return 0  # Mock a successful exit code
            def close(*args):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args, **kwargs):
                pass
        return MockProcess()
    
    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    runner = Runner()
    mock_active_runners[runner.job_id] = runner

    response = client.get(f"/run_session?session_id={runner.job_id}")
    assert response.status_code == 200
    assert "Success" in response.text

# --- Tests for Exception Handlers ---

def test_404():
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert "404" in response.text

@patch("martecompiler.server.server_error")
def test_server_error(mock_server_error):
    mock_server_error.side_effect = Exception("Intentional Test Exception")
    response = client.get("/run_session?session_id=nonexistent")
    assert response.status_code == 500

# --- Tests for Runner Class ---

@patch("os.path.exists", return_value=True)
@patch("os.mkdir")
@patch("shutil.rmtree")
def test_runner_init(mock_rmtree, mock_mkdir, mock_exists):
    runner = Runner()
    assert runner.job_id  # UUID is generated
    mock_exists.assert_called_once()
    mock_rmtree.assert_called_once()
    mock_mkdir.assert_called_once()

@patch("subprocess.Popen")
def test_runner_run(mock_popen):
    runner = Runner()
    mock_process = MagicMock()
    mock_popen.return_value = mock_process
    runner.run()
    mock_popen.assert_called()

# --- Tests for Helper Functions ---

def test_parse_times():
    assert parse_times("2 hours") == 7200
    assert parse_times("1 day 3 hours") == 97200
    with pytest.raises(Exception, match="not a recognised string"):
        parse_times("invalid time")

def test_parse_datasizes():
    assert parse_datasizes("1 GB") == 1000000000
    assert parse_datasizes("500 MB") == 500000000
    with pytest.raises(Exception, match="not a recognised string"):
        parse_datasizes("invalid size")

# --- Tests for FTP and Directory Cleanup Threads ---

@patch("martecompiler.server.FTPServer")
@patch("martecompiler.server.DummyAuthorizer")
def test_runFTP(mock_authorizer, mock_ftp_server):
    mock_server_instance = MagicMock()
    mock_ftp_server.return_value = mock_server_instance
    mock_authorizer_instance = MagicMock()
    mock_authorizer.return_value = mock_authorizer_instance

    run_ftp()
    mock_authorizer.assert_called()
    mock_ftp_server.assert_called()
    mock_server_instance.serve_forever.assert_called_once()

@patch("os.path.exists", return_value=True)
@patch("os.mkdir")
@patch("time.sleep", side_effect=Exception("Exit sleep loop"))
@patch("logging.info")  # Mock logging
def test_cleanDir(mock_log, mock_sleep, mock_mkdir, mock_exists):
    # Exit the infinite loop after initial call to ensure test isolation
    with pytest.raises(Exception, match="Exit sleep loop"):
        server.clean_dir()

    with pytest.raises(Exception, match="Exit sleep loop"):
        backup = copy.copy(server.settings['period'])
        del server.settings['period']
        server.clean_dir()
        server.settings['period'] = backup
    mock_log.assert_any_call(f"Defaulting to running cleanup routine daily. Change in {root_dir}/settings.yml")

    with pytest.raises(Exception, match="Exit sleep loop"):
        backup = copy.copy(server.settings['keep_for'])
        del server.settings['keep_for']
        server.clean_dir()
        server.settings['keep_for'] = backup
    mock_log.assert_any_call(f"Defaulting to never trimming files. Change in {root_dir}/settings.yml")

    with pytest.raises(Exception, match="Exit sleep loop"):
        backup = copy.copy(server.settings['trim_to'])
        del server.settings['trim_to']
        server.clean_dir()
        server.settings['trim_to'] = backup
    mock_log.assert_any_call(f"Defaulting to not limiting max directory size. Change in {root_dir}/settings.yml")

#@patch("martecompiler.server.Runner.run")
def test_run_non_test(monkeypatch):
    response = client.get("/start_session")
    assert response.status_code == 200
    assert response.text  # Job ID should be returned
    def mock_run(self):
        server.running.pop(self.job_id)
    monkeypatch.setattr(martecompiler.server.Runner, "run", mock_run)
    response = client.get(f"/run_session?session_id={response.text}")
    assert response.status_code == 500
    assert "An internal server error occurred." in response.text

@patch("os.mkdir")
@patch("martecompiler.server.FTPServer")
@patch("martecompiler.server.DummyAuthorizer")
def test_mkdir_runFTP(mock_authorizer, mock_ftp_server, mock_mkdir):
    mock_server_instance = MagicMock()
    mock_ftp_server.return_value = mock_server_instance
    mock_authorizer_instance = MagicMock()
    mock_authorizer.return_value = mock_authorizer_instance
    server.settings['temp_directory'] = os.path.join(server.settings['temp_directory'], 'test')
    run_ftp()
    mock_authorizer.assert_called()
    mock_ftp_server.assert_called()
    mock_server_instance.serve_forever.assert_called_once()
    mock_mkdir.assert_called_once()

@patch("time.sleep", side_effect=Exception("Exit sleep loop"))
@patch("os.mkdir")
def test_mkdir_cleanDir(mock_mkdir, mock_sleep):
    server.settings['temp_directory'] = os.path.join(server.settings['temp_directory'], 'test')
    with pytest.raises(Exception, match="Exit sleep loop"):
        server.clean_dir()
    mock_mkdir.assert_called_once()

# Test for delete_generic
@mock.patch("shutil.rmtree")
@mock.patch("os.remove")
def test_delete_generic(mock_remove, mock_rmtree):
    # Test that both shutil.rmtree and os.remove are called when delete_generic is called
    file_path = "/path/to/file"
    delete_generic(file_path)
    
    mock_rmtree.assert_called_once_with(file_path, ignore_errors=True)
    mock_remove.assert_called_once_with(file_path)

# Test for delete_old
@mock.patch("os.path.getmtime")
@mock.patch("martecompiler.server.delete_generic")
@mock.patch("martecompiler.server.log")
def test_delete_old(mock_log, mock_delete_generic, mock_getmtime):
    # Simulate file modification times
    mock_getmtime.side_effect = lambda file: time.time() - 1000  # 1000 seconds ago
    files = ["/path/to/file1"]
    keep_for = 500  # files older than 500 seconds should be deleted
    
    delete_old(files, keep_for)
    
    # Check that the files are deleted because they are older than keep_for
    mock_delete_generic.assert_called_with("/path/to/file1")
    #mock_log.assert_called_with("Deleting /path/to/file1 because it is 1000.0 seconds old")
    assert "Deleting /path/to/file1 because it is " in mock_log.call_args[0][0]
# Test for directory_size
@mock.patch("subprocess.run")
def test_directory_size(mock_run):
    # Simulate subprocess.run to return a mocked output
    mock_run.return_value.stdout = "1024\t/path/to/dir\n"
    file_path = "/path/to/dir"
    
    result = directory_size(file_path)
    
    # Assert that the result is the integer value of the size
    assert result == 1024
    mock_run.assert_called_once_with(['du', '-s', file_path], capture_output=True, text=True, check=False)
