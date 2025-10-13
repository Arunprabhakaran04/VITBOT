from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException, status
from collections import deque
from time import time
from typing import Deque, Dict
import threading
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter.

    Defaults to 5 requests per 1 second per client. Client key is derived from
    Authorization bearer token (user id) when available, otherwise remote IP.

    Notes:
    - This is in-memory and not suitable for multi-process/multi-host deployments.
    - Use Redis-based rate limiting for production across multiple workers.
    """

    def __init__(self, app, calls: int = 5, period: float = 1.0):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.lock = threading.Lock()
        self.requests: Dict[str, Deque[float]] = {}

    def _get_client_key(self, request: Request) -> str:
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            return auth.split(" ", 1)[1].strip()
        # fallback to client IP
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for safe endpoints and preflight
        if request.method == "OPTIONS" or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi") or request.url.path == "/health":
            return await call_next(request)

        key = self._get_client_key(request)
        now = time()

        with self.lock:
            dq = self.requests.get(key)
            if dq is None:
                dq = deque()
                self.requests[key] = dq

            # Remove outdated timestamps
            while dq and dq[0] <= now - self.period:
                dq.popleft()

            if len(dq) >= self.calls:
                # Rate limit exceeded
                logger.info("Rate limit exceeded for %s", key)
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")

            dq.append(now)

        return await call_next(request)
