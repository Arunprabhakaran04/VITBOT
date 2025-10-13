from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException, status
from backend.oauth2 import oauth2_scheme, verify_access_token
from ..services.user_utils import UserUtils
from typing import Callable
import logging

logger = logging.getLogger(__name__)


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce admin role on /admin routes.

    It extracts the bearer token from the Authorization header, verifies it via
    the project's `verify_access_token` helper, and ensures the role is 'admin'.
    If missing or invalid, returns 401/403 accordingly.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Only apply middleware to admin paths
        path = request.url.path
        if not path.startswith("/admin"):
            return await call_next(request)

        # Allow CORS preflight requests to pass through so CORS middleware can handle them
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract Authorization header
        auth: str | None = request.headers.get("authorization")
        if not auth or not auth.lower().startswith("bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization token")

        token = auth.split(" ", 1)[1].strip()

        credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized user")

        try:
            token_data = verify_access_token(token, credential_exception)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Token verification failed: %s", e)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token verification failed")

        # Cross-check role against the database to ensure token hasn't been tampered with
        try:
            db_user = UserUtils.get_user_by_id(token_data.id)
        except Exception as e:
            logger.exception("DB lookup for user failed: %s", e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error validating user role")

        if not db_user:
            # No such user in DB
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        if db_user.get("role") != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        # Attach user info to request.state for downstream handlers if needed
        request.state.current_admin = token_data

        return await call_next(request)
