import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class LoginRateLimiter:
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds
        self._hits[key] = [t for t in self._hits[key] if t > window_start]
        if len(self._hits[key]) >= self.max_requests:
            return False
        self._hits[key].append(now)
        return True

    def reset(self):
        self._hits.clear()


_rate_limiter: LoginRateLimiter | None = None


def get_login_limiter() -> LoginRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = LoginRateLimiter()
    return _rate_limiter


def reset_login_limiter():
    get_login_limiter().reset()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/api/v1/auth/login" and request.method == "POST":
            key = request.client.host if request.client else "unknown"
            if not get_login_limiter().is_allowed(key):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                )
        return await call_next(request)
