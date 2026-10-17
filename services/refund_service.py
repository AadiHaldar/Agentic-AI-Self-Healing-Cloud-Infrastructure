import ast
import hashlib
import json
import logging
import os
import shlex
import sqlite3
import subprocess
import tempfile

import requests
import yaml

logger = logging.getLogger(__name__)

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
    return requests.get(url, timeout=10, verify=True)


def load_config(text):
    return yaml.safe_load(text)


def read_upload(name):
    base_dir = os.path.abspath("/data/uploads")
    safe_path = os.path.abspath(os.path.join(base_dir, name))
    if not safe_path.startswith(base_dir + os.sep) and safe_path != base_dir:
        raise ValueError("Invalid file path")
    with open(safe_path, "r", encoding="utf-8") as f:
        return f.read()


def cleanup():
    cache_path = os.path.join(tempfile.gettempdir(), "cache")
    try:
        os.remove(cache_path)
    except OSError as e:
        logger.warning("Failed to remove cache file %s: %s", cache_path, e)