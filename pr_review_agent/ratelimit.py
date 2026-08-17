"""
pr_review_agent/ratelimit.py — In-memory per-installation sliding-window rate limiter.

Prevents a single GitHub installation from triggering the Gemini pipeline faster
than `max_calls` times per `window_secs` seconds.

Design:
- Sliding window using a deque of timestamps per installation_id.
- Thread-safe via threading.Lock (FastAPI BackgroundTasks run in threads).
- Purely in-memory — resets on process restart (intentional: restarts are cold-starts).
- No external dependency (no Redis, no database).

Defaults: 5 pipeline runs per 60 seconds per installation.
"""
import logging
import threading
import time
from collections import deque
from typing import Dict, Deque

logger = logging.getLogger(__name__)

# Global state: {installation_id: deque of Unix timestamps}
_windows: Dict[int, Deque[float]] = {}
_lock = threading.Lock()


def check_rate_limit(
    installation_id: int,
    *,
    window_secs: int = 60,
    max_calls: int = 5,
) -> bool:
    """
    Return True if the call is allowed, False if it exceeds the rate limit.

    Slides the window to the current time and drops timestamps older than
    `window_secs` before deciding.

    Args:
        installation_id: GitHub App installation identifier (per-org/user).
        window_secs: Length of the sliding window in seconds.
        max_calls: Maximum allowed calls within the window.

    Returns:
        True  → caller may proceed.
        False → caller should drop/reject the request.
    """
    now = time.monotonic()
    cutoff = now - window_secs

    with _lock:
        if installation_id not in _windows:
            _windows[installation_id] = deque()

        window = _windows[installation_id]

        # Evict timestamps outside the current window
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= max_calls:
            logger.warning(
                "[ratelimit] installation_id=%s hit rate limit: %d calls in %ds window",
                installation_id, len(window), window_secs,
            )
            return False

        window.append(now)
        return True


def get_window_stats(installation_id: int, window_secs: int = 60) -> dict:
    """
    Return current call count in the window (for diagnostics / health endpoint).
    """
    now = time.monotonic()
    cutoff = now - window_secs
    with _lock:
        window = _windows.get(installation_id, deque())
        count = sum(1 for t in window if t >= cutoff)
    return {"installation_id": installation_id, "calls_in_window": count, "window_secs": window_secs}


def reset_installation(installation_id: int) -> None:
    """Clear rate-limit state for an installation (e.g., after uninstall event)."""
    with _lock:
        _windows.pop(installation_id, None)
