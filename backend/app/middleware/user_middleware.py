from fastapi import Depends, HTTPException, status
from backend.oauth2 import verify_access_token, oauth2_scheme
from backend.schemas import TokenData
from ..services.user_utils import UserUtils
import logging

logger = logging.getLogger(__name__)


def require_authenticated_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Dependency to require an authenticated user for router-level protection.

    Verifies the access token and confirms the user exists in the database.
    Returns TokenData on success. Raises HTTPException on failure.
    """
    credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized user")
    try:
        token_data = verify_access_token(token, credential_exception)
    except HTTPException as e:
        # Re-raise HTTPException (including token expiration errors)
        raise e
    except Exception as e:
        logger.exception("Token verification failed in dependency: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token verification failed")

    # Ensure user exists in DB
    try:
        db_user = UserUtils.get_user_by_id(token_data.id)
    except Exception as e:
        logger.exception("DB lookup for user failed in dependency: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error validating user")

    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return token_data


def require_user_role(token_data: TokenData = Depends(require_authenticated_user)) -> TokenData:
    """Dependency to ensure the authenticated user has role == 'user'."""
    # Allow both regular users and admins to access user/chat endpoints
    if token_data.role not in ('user', 'admin'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User or admin role required")
    return token_data
