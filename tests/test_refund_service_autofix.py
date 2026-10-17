import json
import sqlite3
from unittest.mock import MagicMock, mock_open, patch
import pytest
import yaml

from services.refund_service import (
    calculate,
    cleanup,
    fetch_remote,
    get_user,
    hash_password,
    load_config,
    load_session,
    read_upload,
    run_report,
)


def test_get_user_normal(tmp_path, monkeypatch):
    db_file = tmp_path / "app.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE users (id INTEGER, name TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice')")
    conn.commit()
    conn.close()

    monkeypatch.chdir(tmp_path)
    user = get_user(1)
    assert user == (1, "Alice")


def test_get_user_sql_injection(tmp_path, monkeypatch):
    db_file = tmp_path / "app.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE users (id INTEGER, name TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice')")
    conn.commit()
    conn.close()

    monkeypatch.chdir(tmp_path)
    user = get_user("1 OR 1=1")
    assert user is None


@patch("subprocess.run")
def test_run_report_normal(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    run_report("echo hello")
    mock_run.assert_called_once_with(["echo", "hello"], shell=False, check=False)


@patch("subprocess.run")
def test_run_report_unsafe_metacharacters(mock_run):
    run_report("echo hello; rm -rf /")
    mock_run.assert_called_once_with(
        ["echo", "hello;", "rm", "-rf", "/"], shell=False, check=False
    )


def test_load_session_normal():
    data = load_session('{"user": "alice", "role": "admin"}')
    assert data == {"user": "alice", "role": "admin"}


def test_load_session_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        load_session("{invalid_json: True}")


def test_calculate_normal():
    assert calculate("[1, 2, 3]") == [1, 2, 3]


def test_calculate_code_injection():
    with pytest.raises((ValueError, SyntaxError)):
        calculate("__import__('os').system('echo pwned')")


def test_hash_password_normal():
    res = hash_password("secret123")
    assert isinstance(res, str)
    assert len(res) == 64


def test_hash_password_unsafe_input():
    res = hash_password("admin' -- \x00")
    assert isinstance(res, str)
    assert len(res) == 64


@patch("requests.get")
def test_fetch_remote_normal(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    fetch_remote("https://example.com/api")
    mock_get.assert_called_once_with("https://example.com/api", timeout=10, verify=True)


def test_fetch_remote_invalid_scheme():
    with pytest.raises(ValueError, match="Invalid URL scheme"):
        fetch_remote("file:///etc/passwd")


def test_load_config_normal():
    res = load_config("key: value")
    assert res == {"key": "value"}


def test_load_config_unsafe_yaml():
    unsafe_yaml = "!!python/object/apply:os.system ['echo pwned']"
    with pytest.raises(yaml.YAMLError):
        load_config(unsafe_yaml)


def test_read_upload_normal():
    m = mock_open(read_data="file data")
    with patch("builtins.open", m):
        content = read_upload("report.txt")
        assert content == "file data"


def test_read_upload_path_traversal():
    with pytest.raises(ValueError, match="Path traversal detected"):
        read_upload("../../etc/passwd")


def test_cleanup_normal(tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    cache_file = tmp_path / "cache"
    cache_file.write_text("temporary data")
    assert cache_file.exists()
    cleanup()
    assert not cache_file.exists()


def test_cleanup_oserror_handled(tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cleanup()
    assert cache_dir.exists()