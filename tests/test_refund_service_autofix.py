import os
import sqlite3
from unittest.mock import MagicMock

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


def test_get_user(tmp_path, monkeypatch):
    db_file = tmp_path / "app.db"
    real_connect = sqlite3.connect
    conn = real_connect(db_file)
    conn.execute("CREATE TABLE users (id INT, name TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice')")
    conn.commit()
    conn.close()

    monkeypatch.setattr("services.refund_service.sqlite3.connect", lambda path: real_connect(db_file))

    user = get_user(1)
    assert user == (1, "Alice")

    user_inj = get_user("1 OR 1=1")
    assert user_inj is None


def test_run_report(monkeypatch):
    calls = []

    def fake_run(cmd, check=True):
        calls.append((cmd, check))
        return MagicMock(returncode=0)

    monkeypatch.setattr("services.refund_service.subprocess.run", fake_run)

    run_report(["ls", "-l"])
    assert calls[-1] == (["ls", "-l"], True)

    run_report("echo hello; rm -rf /")
    assert calls[-1] == (["echo", "hello;", "rm", "-rf", "/"], True)


def test_load_session():
    res = load_session('{"user": "admin"}')
    assert res == {"user": "admin"}

    with pytest.raises(Exception):
        load_session('{"invalid json": ')


def test_calculate():
    res = calculate("[1, 2, 3]")
    assert res == [1, 2, 3]

    with pytest.raises(Exception):
        calculate("__import__('os').system('id')")


def test_hash_password():
    h1 = hash_password("secret123")
    assert isinstance(h1, str) and len(h1) == 64

    h2 = hash_password("' OR '1'='1")
    assert isinstance(h2, str) and len(h2) == 64
    assert h1 != h2


def test_fetch_remote(monkeypatch):
    calls = []

    def fake_get(url, timeout=10):
        calls.append((url, timeout))
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        return mock_resp

    monkeypatch.setattr("services.refund_service.requests.get", fake_get)

    fetch_remote("https://api.example.com/data")
    assert calls[-1] == ("https://api.example.com/data", 10)

    fetch_remote("http://169.254.169.254/latest/meta-data/")
    assert calls[-1] == ("http://169.254.169.254/latest/meta-data/", 10)


def test_load_config():
    cfg = load_config("name: test\ncount: 5")
    assert cfg == {"name": "test", "count": 5}

    with pytest.raises(Exception):
        load_config("!!python/object/apply:os.system ['id']")


def test_read_upload(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    test_file = uploads_dir / "file.txt"
    test_file.write_text("hello content", encoding="utf-8")

    orig_abspath = os.path.abspath

    def fake_abspath(path):
        p_str = str(path)
        if p_str == "/data/uploads":
            return orig_abspath(str(uploads_dir))
        if p_str.startswith("/data/uploads/"):
            rel = p_str[len("/data/uploads/"):]
            return orig_abspath(os.path.join(str(uploads_dir), rel))
        return orig_abspath(p_str)

    monkeypatch.setattr("services.refund_service.os.path.abspath", fake_abspath)

    content = read_upload("file.txt")
    assert content == "hello content"

    with pytest.raises(ValueError, match="Invalid file path"):
        read_upload("../../etc/passwd")


def test_cleanup(tmp_path, monkeypatch):
    monkeypatch.setattr("services.refund_service.tempfile.gettempdir", lambda: str(tmp_path))
    cache_file = tmp_path / "app_cache"
    cache_file.write_text("cache data")

    cleanup()
    assert not cache_file.exists()

    cleanup()