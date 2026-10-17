#!/usr/bin/env python3
"""
Show or change where GitHub delivers the review bot's webhooks (the GitHub App's webhook URL).

    python scripts/switch_webhook.py status
    python scripts/switch_webhook.py --to vm1        # deliver to VM1 (public port 80 via nginx)
    python scripts/switch_webhook.py --to laptop     # deliver to the smee.io relay -> your laptop

Run it from the project folder on the laptop: it signs in as the App with the private key in .env.app.
Only the URL is changed. The webhook secret stays the same, so either receiver accepts the events.
"""
import argparse
import base64
import json
import os
import sys
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

TARGETS = {
    "vm1": "http://20.244.17.209/webhooks/github",
    "laptop": "https://smee.io/bnQuJsrvp8I1iUA",
}


def load_env_app() -> dict:
    out = {}
    with open(os.path.join(ROOT, ".env.app"), encoding="utf-8") as fh:
        for line in fh:
            if "=" in line and not line.startswith("#"):
                k, v = line.rstrip("\n").split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def call(method: str, path: str, jwt: str, body=None):
    req = urllib.request.Request(
        "https://api.github.com" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {jwt}", "Accept": "application/vnd.github+json", "User-Agent": "agentheal-switch",
                 "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode() or "null")


def describe(url: str) -> str:
    for name, target in TARGETS.items():
        if url == target:
            return name
    return "somewhere else"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", nargs="?", choices=["status"], help="show where webhooks go now")
    ap.add_argument("--to", choices=sorted(TARGETS), help="send webhooks to this receiver")
    args = ap.parse_args()
    if not args.action and not args.to:
        ap.print_help()
        return 2

    from pr_review_agent.github_app_auth import generate_jwt
    env = load_env_app()
    jwt = generate_jwt(int(env["GITHUB_APP_ID"]), base64.b64decode(env["GITHUB_APP_PRIVATE_KEY"]).decode())
    app = call("GET", "/app", jwt)
    current = call("GET", "/app/hook/config", jwt).get("url", "")
    print(f"App: {app['slug']}  |  webhooks currently go to: {current}  ({describe(current)})")

    if args.to:
        target = TARGETS[args.to]
        if current == target:
            print(f"Already pointing at {args.to}; nothing to change.")
            return 0
        call("PATCH", "/app/hook/config", jwt, {"url": target, "content_type": "json", "insecure_ssl": "0"})
        now = call("GET", "/app/hook/config", jwt).get("url", "")
        print(f"Changed -> {now}  ({describe(now)})")
        print("Make sure that receiver is running before you open a PR.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
