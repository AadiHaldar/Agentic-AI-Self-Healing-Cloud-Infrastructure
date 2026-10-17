import json
import sqlite3
from unittest.mock import MagicMock, mock_open, patch

import pytest

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
    real_connect = sqlite3.connect
    conn = real_connect(str(db_file))
    conn.execute("CREATE TABLE users (id INT, name TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice')")
    conn.commit()
    conn.close()

    monkeypatch.setattr("services.refund_service.sqlite3.connect", lambda path: real_connect(str(db_file)))
    res = get_user(1)
    assert res == (1, "Alice")


def test_get_user_sql_injection(tmp_path, monkeypatch):
    db_file = tmp_path / "app.db"
    real_connect = sqlite3.connect
    conn = real_connect(str(db_file))
    conn.execute("CREATE TABLE users (id INT, name TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice')")
    conn.commit()
    conn.close()

    monkeypatch.setattr("services.refund_service.sqlite3.connect", lambda path: real_connect(str(db_file)))
    res = get_user("1 OR 1=1")
    assert res is None


def test_run_report_normal():
    with patch("services.refund_service.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        run_report(["echo", "hello"])
        mock_run.assert_called_once_with(["echo", "hello"], check=True)


def test_run_report_unsafe_string():
    with patch("services.refund_service.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        run_report("echo hello; rm -rf /")
        mock_run.assert_called_once_with(["echo", "hello;", "rm", "-rf", "/"], check=True)


def test_load_session_normal():
    data = load_session('{"user": "alice"}')
    assert data == {"user": "alice"}


def test_load_session_invalid():
    with pytest.raises(Exception):
        load_session('{"user": unquoted}')


def test_calculate_normal():
    assert calculate("123") == 123
    assert calculate("[1, 2, 3]") == [1, 2, 3]


def test_calculate_unsafe():
    with pytest.raises(Exception):
        calculate('__import__("os").system("echo 1")')


def test_hash_password_normal():
    res = hash_password("secret")
    assert isinstance(res, str)
    assert len(res) == 64


def test_hash_password_empty():
    res = hash_password("")
    assert isinstance(res, str)
    assert len(res) == 64


def test_fetch_remote_normal():
    with patch("services.refund_service.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        fetch_remote("https://example.com")
        mock_get.assert_called_once_with("https://example.com", timeout=10, verify=True)


def test_fetch_remote_unsafe_url():
    with patch("services.refund_service.requests.get") as mock_get:
        fetch_remote("http://169.254.169.254/latest/meta-data/")
        mock_get.assert_called_once_with("http://169.254.169.254/latest/meta-data/", timeout=10, verify=True)


def test_load_config_normal():
    res = load_config("key: value")
    assert res == {"key": "value"}


def test_load_config_unsafe():
    with pytest.raises(Exception):
        load_config("!!python/object/apply:os.system ['echo 1']")


def test_read_upload_normal():
    with patch("builtins.open", mock_open(read_data="file content")):
        content = read_upload("report.txt")
        assert content == "file content"


def test_read_upload_path_traversal():
    with pytest.raises(ValueError):
        read_upload("../../../etc/passwd")


def test_cleanup_normal(monkeypatch):
    called = []

    def fake_remove(path):
        called.append(path)

    monkeypatch.setattr("services.refund_service.os.remove", fake_remove)
    cleanup()
    assert len(called) == 1


def test_cleanup_oserror(monkeypatch):
    def fake_remove(path):
        raise OSError("File not found")

    monkeypatch.setattr("services.refund_service.os.remove", fake_remove)
    cleanup()