#!/usr/bin/env python3
"""
Reset the live-demo branch to ONE fresh commit on top of origin/main.

Why: GitHub keeps check runs per commit SHA. If the same commit is reused for a second demo,
the PR page shows the previous run's red check immediately and the bot looks like it finished
instantly. A fresh commit means a fresh SHA and a genuinely new review.

Close any open PR from the demo branch BEFORE running this (a force-push to an open PR
would trigger another review).

    python scripts/reset_demo_branch.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BRANCH = "demo/live-review"
ASSET = os.path.join(ROOT, "scripts", "demo_assets", "vulnerable_service.py.txt")
TARGET = "services/refund_service.py"
REPO = "AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure"


def git(*args, cwd=ROOT, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check).stdout.strip()


def main() -> int:
    git("fetch", "-q", "origin", "main")
    name = git("config", "user.name") or "demo"
    email = git("config", "user.email") or "demo@example.com"
    tmp = tempfile.mkdtemp(prefix="agentheal-demo-")
    try:
        git("worktree", "add", "-q", "--detach", tmp, "origin/main")
        os.makedirs(os.path.join(tmp, "services"), exist_ok=True)
        shutil.copy(ASSET, os.path.join(tmp, TARGET))
        git("add", TARGET, cwd=tmp)
        git("-c", f"user.name={name}", "-c", f"user.email={email}", "commit", "-q",
            "-m", f"Add refund service ({time.strftime('%H:%M:%S')})", cwd=tmp)
        sha = git("rev-parse", "HEAD", cwd=tmp)
        git("push", "-q", "--force", "origin", f"HEAD:refs/heads/{BRANCH}", cwd=tmp)
    except subprocess.CalledProcessError as e:
        print("FAILED:", (e.stderr or e.stdout or str(e)).strip()[:300])
        return 1
    finally:
        git("worktree", "remove", "--force", tmp, check=False)
        git("worktree", "prune", check=False)
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"Demo branch '{BRANCH}' reset to fresh commit {sha[:7]} (adds {TARGET}).")
    print(f"Open the PR here:\n  https://github.com/{REPO}/compare/main...{BRANCH}?expand=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
