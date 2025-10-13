import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timedelta, timezone
from backend.schemas import TokenData
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
import os
load_dotenv()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "login")

# Role-based expirations (in minutes). Provide sensible defaults if not set.
# Admin tokens default to 30 minutes; regular user tokens default to 24 hours (1440 minutes).
ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
USER_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("USER_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

def create_access_token(data: dict):
    """Create JWT access token with role-based expiry.

    If the payload contains a 'role' == 'admin', the token TTL will be
    ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES. Otherwise USER_ACCESS_TOKEN_EXPIRE_MINUTES.

    For backward compatibility, if ACCESS_TOKEN_EXPIRE_MINUTES env var is set
    and role-specific env vars are not, it will be used.
    """
    to_encode = data.copy()

    # Determine expiry minutes
    role = data.get("role", "user")
    if role == "admin":
        expire_minutes = ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES
    else:
        expire_minutes = USER_ACCESS_TOKEN_EXPIRE_MINUTES

    # No legacy fallback: use only role-specific TTLs

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token:str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id : int = payload.get("user_id")
        email:str = payload.get("email")
        role:str = payload.get("role", "user")
        if email is None or id is None:
            raise credentials_exception
        token_data = TokenData(id = id, email = email, role = role)
    except ExpiredSignatureError:
        # Specific error for expired token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired. Please login again."
        )
    except InvalidTokenError:
        # Handle malformed or invalid tokens
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token. Please login again."
        )
    except PyJWTError:
        raise credentials_exception
    return token_data

def get_current_user(token : str = Depends(oauth2_scheme)):
    credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail = "unauthorized user")
    
    return verify_access_token(token, credential_exception)

def get_current_admin_user(token : str = Depends(oauth2_scheme)):
    """Get current user and verify admin role"""
    credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail = "unauthorized user")
    user_data = verify_access_token(token, credential_exception)
    
    if user_data.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin access required"
        )
    
    return user_data

def require_role(required_role: str):
    """Decorator to require specific role"""
    def role_checker(token: str = Depends(oauth2_scheme)):
        credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail = "unauthorized user")
        user_data = verify_access_token(token, credential_exception)
        
        if user_data.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return user_data
    
    return role_checker
