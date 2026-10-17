import json
import os
import sqlite3
import tempfile
from unittest.mock import MagicMock

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
    db_path = tmp_path / "app.db"
    real_connect = sqlite3.connect
    conn = real_connect(str(db_path))
    conn.execute("CREATE TABLE users (id TEXT, name TEXT)")
    conn.execute("INSERT INTO users VALUES ('usr_1', 'Alice')")
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        "services.refund_service.sqlite3.connect",
        lambda *args, **kwargs: real_connect(str(db_path)),
    )

    result = get_user("usr_1")
    assert result == ("usr_1", "Alice")


def test_get_user_sqli(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    real_connect = sqlite3.connect
    conn = real_connect(str(db_path))
    conn.execute("CREATE TABLE users (id TEXT, name TEXT)")
    conn.execute("INSERT INTO users VALUES ('usr_1', 'Alice')")
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        "services.refund_service.sqlite3.connect",
        lambda *args, **kwargs: real_connect(str(db_path)),
    )

    sqli_input = "' OR '1'='1"
    result = get_user(sqli_input)
    assert result is None


def test_run_report_normal(monkeypatch):
    mock_run = MagicMock()
    monkeypatch.setattr("services.refund_service.subprocess.run", mock_run)

    run_report("echo hello")
    mock_run.assert_called_once_with(["echo", "hello"], check=True)


def test_run_report_unsafe_cmd(monkeypatch):
    mock_run = MagicMock()
    monkeypatch.setattr("services.refund_service.subprocess.run", mock_run)

    run_report("echo hello; rm -rf /")
    mock_run.assert_called_once_with(
        ["echo", "hello;", "rm", "-rf", "/"], check=True
    )


def test_load_session_normal():
    data = load_session('{"user_id": 123, "role": "admin"}')
    assert data == {"user_id": 123, "role": "admin"}


def test_load_session_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        load_session("{invalid_json}")


def test_calculate_normal():
    assert calculate("123") == 123
    assert calculate("[1, 2, 3]") == [1, 2, 3]


def test_calculate_unsafe_code():
    with pytest.raises((ValueError, SyntaxError, TypeError)):
        calculate("__import__('os').system('echo pwned')")


def test_hash_password_normal():
    h1 = hash_password("secret123")
    assert isinstance(h1, str)
    assert len(h1) == 64


def test_hash_password_unsafe_input():
    h1 = hash_password("' OR '1'='1")
    assert isinstance(h1, str)
    assert len(h1) == 64


def test_fetch_remote_normal(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr("services.refund_service.requests.get", mock_get)

    res = fetch_remote("https://example.com/api")
    assert res.status_code == 200
    mock_get.assert_called_once_with("https://example.com/api", timeout=10)


def test_fetch_remote_ssrf(monkeypatch):
    mock_response = MagicMock()
    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr("services.refund_service.requests.get", mock_get)

    fetch_remote("http://169.254.169.254/latest/meta-data/")
    mock_get.assert_called_once_with(
        "http://169.254.169.254/latest/meta-data/", timeout=10
    )


def test_load_config_normal():
    cfg = load_config("name: test\nversion: 1.0")
    assert cfg == {"name": "test", "version": 1.0}


def test_load_config_unsafe_yaml():
    unsafe_yaml = "!!python/object/apply:os.system ['echo pwned']"
    with pytest.raises(yaml.YAMLError):
        load_config(unsafe_yaml)


def test_read_upload_normal(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    target_file = upload_dir / "test.txt"
    target_file.write_text("hello content", encoding="utf-8")

    def mock_abspath(path):
        if path == "/data/uploads":
            return str(upload_dir)
        return os.path.normpath(path)

    monkeypatch.setattr("services.refund_service.os.path.abspath", mock_abspath)

    res = read_upload("test.txt")
    assert res == "hello content"


def test_read_upload_path_traversal(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    def mock_abspath(path):
        if path == "/data/uploads":
            return str(upload_dir)
        return os.path.normpath(path)

    monkeypatch.setattr("services.refund_service.os.path.abspath", mock_abspath)

    with pytest.raises(ValueError, match="Invalid file path"):
        read_upload("../secret.txt")


def test_cleanup_normal(tmp_path, monkeypatch):
    cache_file = tmp_path / "cache"
    cache_file.write_text("cache data")

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

    cleanup()
    assert not cache_file.exists()


def test_cleanup_os_error(tmp_path, monkeypatch):
    cache_file = tmp_path / "cache"
    cache_file.write_text("cache data")

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

    def mock_remove(path):
        raise OSError("Permission denied")

    monkeypatch.setattr(os, "remove", mock_remove)

    cleanup()