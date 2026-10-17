import json
import sqlite3
import tempfile
from pathlib import Path
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
    monkeypatch.chdir(tmp_path)
    with sqlite3.connect("app.db") as conn:
        conn.execute("CREATE TABLE users (id TEXT, name TEXT)")
        conn.execute("INSERT INTO users VALUES ('1', 'Alice')")
        conn.commit()

    user = get_user("1")
    assert user == ("1", "Alice")


def test_get_user_sqli(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with sqlite3.connect("app.db") as conn:
        conn.execute("CREATE TABLE users (id TEXT, name TEXT)")
        conn.execute("INSERT INTO users VALUES ('1', 'Alice')")
        conn.commit()

    user = get_user("1' OR '1'='1")
    assert user is None


def test_run_report_normal(monkeypatch):
    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)

    run_report("report_gen --date 2023-01-01")
    mock_run.assert_called_once_with(["report_gen", "--date", "2023-01-01"], check=True)


def test_run_report_shell_metacharacters(monkeypatch):
    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)

    run_report("report_gen; rm -rf /")
    mock_run.assert_called_once_with(["report_gen;", "rm", "-rf", "/"], check=True)


def test_load_session_normal():
    data = load_session('{"user_id": 42, "role": "admin"}')
    assert data == {"user_id": 42, "role": "admin"}


def test_load_session_invalid():
    with pytest.raises(json.JSONDecodeError):
        load_session("{user_id: 42, invalid}")


def test_calculate_normal():
    res = calculate("[1, 2, 3]")
    assert res == [1, 2, 3]


def test_calculate_unsafe_code():
    with pytest.raises(ValueError):
        calculate("__import__('os').system('ls')")


def test_hash_password_normal():
    hashed = hash_password("secure_password_123")
    assert isinstance(hashed, str)
    assert len(hashed) == 64


def test_hash_password_unsafe_input():
    hashed = hash_password("admin' --; DROP TABLE users;")
    assert isinstance(hashed, str)
    assert len(hashed) == 64


def test_fetch_remote_normal(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr("requests.get", mock_get)

    res = fetch_remote("https://example.com/api")
    assert res == mock_response
    mock_get.assert_called_once_with("https://example.com/api", timeout=10)


def test_fetch_remote_unsafe_scheme():
    with pytest.raises(ValueError, match="Invalid URL scheme"):
        fetch_remote("file:///etc/passwd")


def test_load_config_normal():
    config = load_config("db:\n  host: localhost\n  port: 5432")
    assert config == {"db": {"host": "localhost", "port": 5432}}


def test_load_config_unsafe_yaml():
    unsafe_payload = "!!python/object/apply:os.system ['id']"
    with pytest.raises(yaml.YAMLError):
        load_config(unsafe_payload)


def test_read_upload_normal(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    file_path = uploads_dir / "report.txt"
    file_path.write_text("sample content", encoding="utf-8")

    def mock_path(p):
        if str(p) == "/data/uploads":
            return uploads_dir
        return Path(p)

    monkeypatch.setattr("services.refund_service.Path", mock_path)

    content = read_upload("report.txt")
    assert content == "sample content"


def test_read_upload_path_traversal(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()

    def mock_path(p):
        if str(p) == "/data/uploads":
            return uploads_dir
        return Path(p)

    monkeypatch.setattr("services.refund_service.Path", mock_path)

    with pytest.raises(ValueError, match="Invalid path"):
        read_upload("../../../etc/passwd")


def test_cleanup_normal(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    cache_file = tmp_path / "cache"
    cache_file.write_text("cached data")

    cleanup()
    assert not cache_file.exists()


def test_cleanup_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    cache_file = tmp_path / "cache"
    if cache_file.exists():
        cache_file.unlink()

    cleanup()