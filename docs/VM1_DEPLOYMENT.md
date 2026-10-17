# VM1 deployment

VM1 (`20.244.17.209`, Ubuntu 24.04, Central India, Azure resource group `VM1_group`) runs a complete copy of the platform **in parallel with the laptop**.
The laptop path stays the live one until you switch the GitHub App's webhook (see "Switching").

```
 GitHub ──webhook──► smee.io relay ──► laptop :8000   (live today)
    │
    └─ (after switching) ──► http://20.244.17.209/webhooks/github ──► nginx :80 ──► 127.0.0.1:8000 (agentic-ai, user agentheal)
```

## What is installed

| Piece | Where | Notes |
|---|---|---|
| App code (current `main`) | `/opt/agentic-ai`, built from the clone in `/opt/agentic-src` | updated by `agentheal-deploy` |
| Service | `systemd` unit `agentic-ai` (`infrastructure/vm1/agentic-ai.service`) | runs as the **unprivileged user `agentheal`** (no shell, no sudo); `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=full`, `ProtectHome`; listens on **127.0.0.1:8000 only** |
| Public front door | nginx on port 80 (`infrastructure/vm1/nginx-agentic-ai-webhook.conf`) | **no login.** Public: the signed `/webhooks/github`, the console (`/`, `/assets/`), read-only data (`GET /api/meta|status|topology|repos|pr-reviews|service-health`), and three demo calls (`POST /api/evaluate|owasp/scan|topology/reset`, rate limited to 20/min per IP). Everything else returns `403`: `/api/override`, `/api/learnings/dismiss`, `/api/seed-demo`, `/api/github/create-pr`, `/api/github/webhook`, `/api/security/send-alert-email`, `/install`, `/api/github/app-callback`, `/docs` |
| Firewall (NSG `VM1-nsg`) | inbound 22 (SSH) and 80 (HTTP) from anywhere | set by the VM owner |
| GitHub App credentials | `/opt/agentic-ai/.env.app` (owner `agentheal`, mode 600) | App ID, slug, webhook secret, private key |
| Gemini key | `/etc/agentic-ai.env` (owner root, mode 600) | read by systemd, not by the app user directly |
| Database | `/opt/agentic-ai/data/pr_review_agent.db` (SQLite, WAL) | nightly backup at 03:00 to `/opt/agentic-ai/backups` (last 7 kept) by `agentheal-backup` |
| Scanners | Ruff, Bandit, detect-secrets, pip-audit in the venv | used by the PR review pipeline |
| Flags | `SEED_DEMO_DATA=0`, `AUTOFIX_RUN_TESTS=1` | auto-fix runs the tests it generates, as the unprivileged user |

Not present on purpose / not done: no TLS (no domain; GitHub accepts an HTTP webhook URL, the payload is signed with HMAC-SHA256),
no Kubernetes or `kubectl` (so actions are plan-only dry runs), no login on the console. Instead of authentication, nginx whitelists the endpoints the console needs and closes every mutating one.

Public console: **http://20.244.17.209/**. Things to know when showing it:
- The PR Review page lists live pull requests from GitHub; the Overview page shows review history imported from the laptop database.
- Self-Healing runs from visitors share one digital-twin state (use "Reset twin") and each costs a Gemini call; the rate limit keeps this bounded.
- `/install` and `/api/github/app-callback` are closed on purpose: whoever reached them could register or overwrite the GitHub App credentials. To re-register the App, use the SSH tunnel.

## Everyday commands (on VM1)

```bash
agentheal-deploy                                   # pull main, build the console, sync, restart, health-check
sudo systemctl status agentic-ai --no-pager
sudo journalctl -u agentic-ai -f                   # live log: webhook received, scanners, Gemini, posted comments
curl -s http://127.0.0.1:8000/api/meta             # what is configured (Gemini, cluster, model, webhook router)
sudo /usr/bin/python3 /usr/local/bin/agentheal-backup   # manual DB backup
```

The console is public at `http://20.244.17.209/`. For the closed routes (override, seed, App registration) open a tunnel from the laptop:

```powershell
ssh -i collaborator_key -N -L 8001:127.0.0.1:8000 collaborator@20.244.17.209
```

then browse to `http://127.0.0.1:8001`.

## Switching the webhook between the laptop and VM1

```powershell
python scripts\switch_webhook.py status        # where do GitHub's webhooks go right now?
python scripts\switch_webhook.py --to vm1      # deliver to VM1 (laptop can be switched off)
python scripts\switch_webhook.py --to laptop   # back to the smee relay and the laptop
```

It changes only the URL; the secret is the same on both receivers. Run `scripts\live_demo.ps1` on the laptop before switching back.
Only one receiver gets events at a time, so a PR is never reviewed twice.

## What was tested (17 October 2026)

| Test | Result |
|---|---|
| Service starts as `agentheal`, Gemini connected, anomaly model trained, webhook router mounted | yes |
| The VM signs in as the GitHub App with the installed credentials and sees only the one repository | yes |
| Signed `pull_request` event sent through the **public port 80** (nginx): bad signature → 401, good signature → accepted | yes |
| Full PR review run on VM1 (static tools, Gemini, summary comment, 22 inline comments, failing quality gate) | **35 s** |
| `scripts/demo_e2e.py` through a tunnel: scanner, webhook checks, five fault scenarios with live Gemini, forced false alarm | **16 / 16** |
| Auto-fix triggered with a signed `@review-bot /fix` event: repaired file + generated tests, new PR into the PR's branch | **101 s**, 9 generated tests passed |
| Unit tests on VM1 | 61 pass |

The review and fix tests were driven by signed synthetic events, so the GitHub App's webhook was **not** moved; the laptop stayed the live receiver throughout.

## Caveats

- VM1 belongs to another person's Azure subscription (your account has Contributor on `VM1_group`). Keep that in mind before storing more secrets there.
- Auto-fix executes model-written tests. On VM1 that runs as the unprivileged `agentheal` user inside the systemd sandbox, but it is still code execution; turn it off with `AUTOFIX_RUN_TESTS=0` in the unit if the VM ever reviews pull requests from strangers.
- HTTP only: the webhook is authenticated by signature, not encrypted in transit. Add a domain and TLS (for example with Let's Encrypt) before treating this as production.
- If the VM is restarted the service starts automatically (`systemctl enable`); the nginx site is already enabled.
