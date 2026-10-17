import hashlib
import os
import pickle
import sqlite3
import subprocess

import requests
import yaml

DB_PASSWORD = "hunter2-demo-password"


def get_user(uid):
    conn = sqlite3.connect("app.db")
    return conn.execute(f"SELECT * FROM users WHERE id = '{uid}'").fetchone()


def run_report(cmd):
    return subprocess.run(cmd, shell=True)


def load_session(blob):
    return pickle.loads(blob)


def calculate(expr):
    return eval(expr)


def hash_password(pw):
    return hashlib.md5(pw.encode()).hexdigest()


def fetch_remote(url):
    return requests.get(url, verify=False)


def load_config(text):
    return yaml.load(text)


def read_upload(name):
    return open(os.path.join("/data/uploads", name)).read()


def cleanup():
    try:
        os.remove("/tmp/cache")
    except Exception:
        pass
