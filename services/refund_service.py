import ast
import hashlib
import json
import logging
import os
import shlex
import sqlite3
import subprocess
import tempfile
from urllib.parse import urlparse

import requests
import yaml

logger = logging.getLogger(__name__)

DB_PASSWORD = os.getenv("DB_PASSWORD", "")


def get_user(uid):
    conn = sqlite3.connect("app.db")
    return conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


def run_report(cmd):
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    return subprocess.run(cmd, shell=False, check=False)


def load_session(blob):
    return json.loads(blob)


def calculate(expr):
    return ast.literal_eval(expr)


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def fetch_remote(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https"):
        raise ValueError("Invalid URL scheme")
    return requests.get(url, timeout=10)


def load_config(text):
    return yaml.safe_load(text)


def read_upload(name):
    base_dir = os.path.abspath("/data/uploads")
    target_path = os.path.abspath(os.path.join(base_dir, name))
    if not target_path.startswith(base_dir + os.sep) and target_path != base_dir:
        raise ValueError("Access denied: Invalid file path")
    with open(target_path, "r", encoding="utf-8") as f:
        return f.read()


def cleanup():
    cache_path = os.path.join(tempfile.gettempdir(), "cache")
    try:
        if os.path.exists(cache_path):
            os.remove(cache_path)
    except OSError as err:
        logger.warning("Failed to clean up cache file: %s", err)