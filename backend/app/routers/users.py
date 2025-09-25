from fastapi import FastAPI, HTTPException, status, APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from passlib.context import CryptContext
from psycopg2 import connect, errors
from psycopg2.extras import RealDictCursor
from ...schemas import usercreate, userout, Post
from ...database_connection import get_db_connection
from ...util import encrypt, verify
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from ...oauth2 import create_access_token, verify_access_token

router = APIRouter()

class UserLogin(BaseModel):
    email: str
    password: str

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=userout)
async def create_user(user: usercreate):
    with get_db_connection() as conn:
        try:
            cursor = conn.cursor()
            password = encrypt(user.password)
            user.password = password
            cursor.execute(
                "INSERT INTO users (email, password) VALUES (%s, %s) RETURNING *",
                (user.email, user.password)
            )
            new_user = cursor.fetchone()
            conn.commit()
            return new_user

        except errors.UniqueViolation:
            conn.rollback()  # roll back failed transaction
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        except Exception as e:
            conn.rollback()  # any other error should also rollback
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

@router.post("/login")
async def login_user(userdata : UserLogin):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s",(userdata.email,))
        user = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found")
        if not verify(userdata.password, user["password"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail = "password incorrect")
        else:
            access_token = create_access_token(data = {"user_id" : user["id"], "email" : user["email"]})
            return {"access_token":  access_token, "token_type" : "bearer"}
    