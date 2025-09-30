import jwt
from jwt.exceptions import PyJWTError
from datetime import datetime, timedelta
from backend.schemas import TokenData
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
import os
load_dotenv()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "login")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

def create_access_token(data:dict):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp" : expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm = ALGORITHM)
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
