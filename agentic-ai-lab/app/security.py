"""
Security helpers: client-IP extraction, constant-time compare, sliding-window
rate limiting, and login brute-force lockout. In-memory (single container) —
state resets on restart, which is fine for this app.
"""

import hmac
import threading
from collections import defaultdict, deque


def client_ip(request) -> str:
    """Real client IP. Behind Traefik the client is the first X-Forwarded-For."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xr = request.headers.get("x-real-ip")
    if xr:
        return xr.strip()
    return request.client.host if request.client else "unknown"


def constant_time_eq(a: str, b: str) -> bool:
    """Timing-attack-resistant string comparison."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


class SlidingWindowLimiter:
    """Allow at most `limit` events per `window` seconds per key (e.g. per IP)."""

    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, now: float) -> bool:
        """Record an event; return True if allowed, False if over the limit."""
        with self._lock:
            dq = self._hits[key]
            cutoff = now - self.window
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= self.limit:
                return False
            dq.append(now)
            return True


class LoginGuard:
    """Per-IP failed-login tracking with temporary lockout."""

    def __init__(self, max_fails: int, window: int, lockout: int):
        self.max_fails = max_fails
        self.window = window
        self.lockout = lockout
        self._fails = defaultdict(deque)     # ip -> deque[timestamps]
        self._locked_until = {}              # ip -> timestamp
        self._lock = threading.Lock()

    def locked_for(self, ip: str, now: float) -> int:
        """Seconds remaining in lockout for this IP (0 if not locked)."""
        with self._lock:
            until = self._locked_until.get(ip, 0)
            return int(until - now) if until > now else 0

    def record_fail(self, ip: str, now: float) -> None:
        with self._lock:
            dq = self._fails[ip]
            cutoff = now - self.window
            while dq and dq[0] < cutoff:
                dq.popleft()
            dq.append(now)
            if len(dq) >= self.max_fails:
                self._locked_until[ip] = now + self.lockout
                dq.clear()

    def reset(self, ip: str) -> None:
        with self._lock:
            self._fails.pop(ip, None)
            self._locked_until.pop(ip, None)
