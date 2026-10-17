import ast
import hashlib
import json
import logging
import os
import shlex
import sqlite3
import subprocess
import tempfile
from pathlib import Path

import requests
import yaml

DB_PASSWORD = os.getenv("DB_PASSWORD", "")


def get_user(uid):
    with sqlite3.connect("app.db") as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


def run_report(cmd):
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    return subprocess.run(cmd, check=True)


def load_session(blob):
    return json.loads(blob)


def calculate(expr):
    return ast.literal_eval(expr)


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def fetch_remote(url):
    if not url.startswith(("http://", "https://")):
        raise ValueError("Invalid URL scheme")
    return requests.get(url, timeout=10)


def load_config(text):
    return yaml.safe_load(text)


def read_upload(name):
    base_dir = Path("/data/uploads").resolve()
    file_path = (base_dir / name).resolve()
    if not file_path.is_relative_to(base_dir):
        raise ValueError("Invalid path")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def cleanup():
    cache_path = os.path.join(tempfile.gettempdir(), "cache")
    try:
        if os.path.exists(cache_path):
            os.remove(cache_path)
    except OSError as err:
        logging.warning("Failed to delete cache file: %s", err)