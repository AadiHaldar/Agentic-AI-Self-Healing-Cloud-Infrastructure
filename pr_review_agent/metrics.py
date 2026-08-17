"""
pr_review_agent/metrics.py — Lightweight in-memory observability counters.

Tracks key health signals for the `/api/service-health` endpoint.
Thread-safe via atomic operations (threading.Lock per counter).

No external dependency. Counters reset on process restart — this is intentional;
they reflect the current process's health, not historical totals (use the
review_log table for historical query).

Available counters
------------------
webhooks_received       : total POST /webhooks/github calls
webhooks_deduplicated   : calls rejected due to duplicate X-GitHub-Delivery
webhooks_rate_limited   : calls rejected by per-installation rate limiter
pipeline_enqueued       : background pipeline tasks queued
pipeline_ok             : background pipeline tasks completed successfully
pipeline_failed         : background pipeline tasks that raised an exception
chat_enqueued           : background chat_handler tasks queued
chat_ok                 : chat_handler tasks completed successfully
chat_failed             : chat_handler tasks that raised an exception
"""
import threading
import time
from typing import Dict

_lock = threading.Lock()

# ── Counter store ─────────────────────────────────────────────────────────────
_counters: Dict[str, int] = {
    "webhooks_received": 0,
    "webhooks_deduplicated": 0,
    "webhooks_rate_limited": 0,
    "pipeline_enqueued": 0,
    "pipeline_ok": 0,
    "pipeline_failed": 0,
    "chat_enqueued": 0,
    "chat_ok": 0,
    "chat_failed": 0,
}

# Process start time (for uptime calculation)
_start_time: float = time.time()


def inc(counter: str, amount: int = 1) -> None:
    """Increment a named counter by `amount` (default 1). Thread-safe."""
    with _lock:
        if counter in _counters:
            _counters[counter] += amount
        else:
            _counters[counter] = amount


def snapshot() -> Dict[str, object]:
    """
    Return a copy of all counters plus derived metrics.
    Safe to call from any thread.
    """
    with _lock:
        data = dict(_counters)

    uptime_secs = time.time() - _start_time
    total_pipeline = data["pipeline_ok"] + data["pipeline_failed"]
    total_chat = data["chat_ok"] + data["chat_failed"]

    data["uptime_seconds"] = round(uptime_secs, 1)
    data["pipeline_success_rate"] = (
        round(data["pipeline_ok"] / total_pipeline, 4) if total_pipeline else None
    )
    data["chat_success_rate"] = (
        round(data["chat_ok"] / total_chat, 4) if total_chat else None
    )
    return data


def reset_all() -> None:
    """Reset all counters to zero (useful in tests)."""
    with _lock:
        for key in _counters:
            _counters[key] = 0
