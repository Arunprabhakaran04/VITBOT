from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class usercreate(BaseModel):
    email: EmailStr
    password: str
    
class userout(BaseModel):
    id : int
    created_at : datetime
    
class Post(BaseModel):
    id:Optional[int] = 1
    title : str
    content : str
    published : Optional[bool] = True
    
class user_message(BaseModel):
    user_message : str
    
class TokenData(BaseModel):
    id : int
    email : EmailStr

class UserTaskStatus(BaseModel):
    task_id: str
    task_type: str
    status: str
    filename: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    progress_message: Optional[str] = None

class UserTasksResponse(BaseModel):
    user_id: int
    active_tasks: List[UserTaskStatus]
    completed_tasks: List[UserTaskStatus]
    total_active: int
    total_completed: int