from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class usercreate(BaseModel):
    email: EmailStr
    password: str
    
class userout(BaseModel):
    id : int
    email : EmailStr
    role : str
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
    role : str = 'user'

class AdminDocument(BaseModel):
    id: Optional[int] = None
    filename: str
    original_filename: str
    file_path: str
    file_size: Optional[int] = None
    document_hash: Optional[str] = None
    uploaded_by: int
    processing_status: str = 'pending'
    vector_store_path: Optional[str] = None
    language: str = 'english'
    embedding_model: str = 'BAAI/bge-small-en-v1.5'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True

class AdminDocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: Optional[int]
    processing_status: str
    language: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

class AdminDocumentsListResponse(BaseModel):
    documents: List[AdminDocumentResponse]
    total_count: int
    active_count: int

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