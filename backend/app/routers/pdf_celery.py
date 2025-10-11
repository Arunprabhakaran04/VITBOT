from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from ...oauth2 import get_current_user
from ..utils.file_utils import save_pdf_file
from ..services.pdf_processing_service import pdf_processing_service
from ..services.background_task_service import background_service
from ..services.task_service import TaskService
from ...schemas import UserTasksResponse
from ..services.rag_handler import clear_user_cache
from loguru import logger
import os
import shutil

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@router.post("/upload_pdf", status_code=202)
async def upload_pdf(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    user_data = get_current_user(token)
    user_id = user_data.id

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    try:
        from ..config.settings import settings
        
        # Validate file size
        content = await file.read()
        file_size = len(content)
        
        if file_size > settings.get_max_file_size_bytes():
            raise HTTPException(
                status_code=413, 
                detail=f"File size exceeds {settings.MAX_FILE_SIZE_MB}MB limit"
            )
        
        # Reset file position for save_pdf_file
        await file.seek(0)
        
        cleanup_existing_vectorstore(user_id)
        
        file_path = save_pdf_file(file, user_id)
        logger.info(f"PDF saved to: {file_path}")

        # Queue the task with background service
        task_id = pdf_processing_service.queue_pdf_processing(user_id, file_path, file.filename)
        
        return {
            "message": "PDF uploaded successfully and queued for processing",
            "task_id": task_id,
            "status": "queued"
        }

    except Exception as e:
        logger.error(f"Error in upload_pdf: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task_status/{task_id}")
async def get_task_status(task_id: str, token: str = Depends(oauth2_scheme)):
    """Get the status of a specific task"""
    user_data = get_current_user(token)
    
    # Get task info from background service
    background_task = background_service.get_task_status(task_id)
    
    # Get database task info for validation
    task_info = TaskService.get_task_info(task_id)
    
    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify task belongs to the user
    if task_info['user_id'] != user_data.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Combine background task status with database info
    status_info = {
        'task_id': task_info['task_id'],
        'task_type': task_info['task_type'],
        'status': task_info['status'],
        'filename': task_info['filename'],
        'message': task_info['progress_message'],
        'created_at': task_info['created_at'],
        'updated_at': task_info['updated_at']
    }
    
    # Add real-time info if available
    if background_task:
        status_info.update({
            'progress': background_task.progress,
            'real_time_status': background_task.status.value,
            'real_time_message': background_task.message
        })
    
    return status_info

@router.get("/processing_status", response_model=UserTasksResponse)
async def get_user_processing_status(token: str = Depends(oauth2_scheme)):
    """Get all tasks for the current user - Production version"""
    user_data = get_current_user(token)
    
    try:
        # Get comprehensive task summary
        tasks_summary = TaskService.get_user_tasks_summary(user_data.id)
        
        return UserTasksResponse(
            user_id=tasks_summary['user_id'],
            active_tasks=tasks_summary['active_tasks'],
            completed_tasks=tasks_summary['completed_tasks'],
            total_active=tasks_summary['total_active'],
            total_completed=tasks_summary['total_completed']
        )
    except Exception as e:
        logger.error(f"Error getting user processing status: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to fetch task status")

def cleanup_existing_vectorstore(user_id: int):
    try:
        from ..services.rag_service import DocumentProcessor
        processor = DocumentProcessor()
        user_vector_dir = os.path.join(processor.vector_store_dir, f"user_{user_id}")
        if os.path.exists(user_vector_dir):
            shutil.rmtree(user_vector_dir)
            logger.info(f"Cleaned up existing vector store for user {user_id}")
    except Exception as e:
        logger.warning(f"Could not clean up existing vector store: {e}")    # Clear the in-memory cache for this user
    clear_user_cache(user_id)

@router.post("/cleanup_old_tasks")
async def cleanup_old_tasks(token: str = Depends(oauth2_scheme)):
    """Clean up old completed/failed tasks (for maintenance)"""
    user_data = get_current_user(token)
    
    try:
        deleted_count = TaskService.cleanup_old_tasks(days_old=30)
        return {
            "message": f"Cleaned up {deleted_count} old tasks",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error cleaning up old tasks: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to cleanup old tasks")

def cleanup_user_data(user_id: int):
    # Clean up vector store
    try:
        from ..services.rag_service import DocumentProcessor
        processor = DocumentProcessor()
        user_vector_dir = os.path.join(processor.vector_store_dir, f"user_{user_id}")
        if os.path.exists(user_vector_dir):
            shutil.rmtree(user_vector_dir)
            logger.info(f"Cleaned up vector store for user {user_id}")
    except Exception as e:
        logger.warning(f"Could not clean up vector store: {e}")    # Clean up uploads
    try:
        from ..utils.file_utils import get_user_upload_dir
        user_upload_dir = get_user_upload_dir(user_id)
        if os.path.exists(user_upload_dir):
            shutil.rmtree(user_upload_dir)
            logger.info(f"Cleaned up uploads for user {user_id}")
    except Exception as e:
        logger.warning(f"Could not clean up uploads: {e}")    # Clear the in-memory cache for this user
    clear_user_cache(user_id)

@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    user_data = get_current_user(token)
    cleanup_user_data(user_data.id)
    return {"message": "Logged out successfully, all user data cleaned up"} 