"""
Admin Router - Admin-only endpoints for document management
"""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from typing import List
import os
import shutil
from loguru import logger

from ...oauth2 import get_current_admin_user
from ...schemas import TokenData, AdminDocumentsListResponse, AdminDocumentResponse
from ..services.admin_document_service import AdminDocumentService, GlobalVectorStoreService
from ..utils.file_utils import get_user_upload_dir
from ..services.task_service import TaskService
from ..services.rag_handler import clear_global_cache
from ...tasks import process_admin_pdf_task

router = APIRouter(prefix="/admin", tags=["admin"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@router.get("/documents", response_model=AdminDocumentsListResponse)
async def get_admin_documents(current_admin: TokenData = Depends(get_current_admin_user)):
    """Get all admin documents"""
    try:
        documents = AdminDocumentService.get_all_active_documents()
        summary = AdminDocumentService.get_documents_summary()
        
        return AdminDocumentsListResponse(
            documents=documents,
            total_count=summary.get('total', 0),
            active_count=summary.get('active', 0)
        )
    except Exception as e:
        logger.error(f"Error fetching admin documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching documents")

@router.post("/documents/upload", status_code=202)
async def upload_admin_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    current_admin: TokenData = Depends(get_current_admin_user)
):
    """Upload PDF document to admin knowledge base"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    try:
        # Create admin upload directory
        admin_upload_dir = os.path.join(
            os.path.dirname(__file__), 
            "../../uploads/admin_documents"
        )
        os.makedirs(admin_upload_dir, exist_ok=True)
        
        # Generate unique filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
        file_path = os.path.join(admin_upload_dir, safe_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(file_path)
        
        # Create database record
        document_record = AdminDocumentService.create_admin_document(
            filename=safe_filename,
            original_filename=file.filename,
            file_path=file_path,
            uploaded_by=current_admin.id,
            file_size=file_size
        )
        
        # Queue processing task
        task = process_admin_pdf_task.delay(
            document_record['id'], 
            file_path, 
            file.filename
        )
        
        # Track task
        TaskService.store_user_task(
            current_admin.id, 
            task.id, 
            "admin_pdf_processing", 
            file.filename
        )
        
        logger.info(f"Admin document uploaded: {file.filename} by user {current_admin.id}")
        
        return {
            "message": "Document uploaded successfully and queued for processing",
            "document_id": document_record['id'],
            "task_id": task.id,
            "status": "queued"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in admin document upload: {str(e)}")
        raise HTTPException(status_code=500, detail="Error uploading document")

@router.get("/documents/{document_id}")
async def get_admin_document(
    document_id: int, 
    current_admin: TokenData = Depends(get_current_admin_user)
):
    """Get specific admin document details"""
    document = AdminDocumentService.get_document_by_id(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document

@router.delete("/documents/{document_id}")
async def delete_admin_document(
    document_id: int, 
    current_admin: TokenData = Depends(get_current_admin_user)
):
    """Delete admin document (soft delete) and remove from global vector store"""
    try:
        # Get document info before deletion
        document = AdminDocumentService.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Remove from global vector store using the new manager
        from ..services.global_vector_store_manager import GlobalVectorStoreManager
        global_manager = GlobalVectorStoreManager()
        
        # Remove from global vector store
        removal_success = global_manager.remove_document_from_global_store(document_id)
        
        if not removal_success:
            logger.warning(f"Failed to remove document {document_id} from global vector store")
        
        # Soft delete the document record
        success = AdminDocumentService.delete_document(document_id, soft_delete=True)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found or already deleted")
        
        # Get updated stats
        stats = global_manager.get_global_store_stats()
        
        # Clear global cache since admin documents changed
        clear_global_cache()
        
        logger.info(f"Admin document {document_id} ({document['original_filename']}) deleted by user {current_admin.id}")
        
        return {
            "message": "Document deleted successfully and removed from global knowledge base",
            "document_id": document_id,
            "filename": document['original_filename'],
            "global_stats": {
                "total_vectors": stats['total_vectors'],
                "total_documents": stats['total_documents']
            }
        }
        
    except Exception as e:
        logger.error(f"Error deleting admin document: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting document")

@router.delete("/documents/{document_id}/force")
async def force_delete_admin_document(
    document_id: int, 
    current_admin: TokenData = Depends(get_current_admin_user)
):
    """Force delete admin document (hard delete) - removes file and all records"""
    try:
        # Get document info before deletion
        document = AdminDocumentService.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Remove from global vector store
        from ..services.global_vector_store_manager import GlobalVectorStoreManager
        global_manager = GlobalVectorStoreManager()
        removal_success = global_manager.remove_document_from_global_store(document_id)
        
        # Delete physical file
        file_deleted = False
        if document.get('file_path') and os.path.exists(document['file_path']):
            try:
                os.remove(document['file_path'])
                file_deleted = True
                logger.info(f"Deleted physical file: {document['file_path']}")
            except Exception as e:
                logger.warning(f"Failed to delete physical file: {e}")
        
        # Hard delete the document record
        success = AdminDocumentService.delete_document(document_id, soft_delete=False)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get updated stats
        stats = global_manager.get_global_store_stats()
        
        # Clear global cache
        clear_global_cache()
        
        logger.info(f"Admin document {document_id} ({document['original_filename']}) force deleted by user {current_admin.id}")
        
        return {
            "message": "Document permanently deleted",
            "document_id": document_id,
            "filename": document['original_filename'],
            "file_deleted": file_deleted,
            "vector_store_updated": removal_success,
            "global_stats": {
                "total_vectors": stats['total_vectors'],
                "total_documents": stats['total_documents']
            }
        }
        
    except Exception as e:
        logger.error(f"Error force deleting admin document: {str(e)}")
        raise HTTPException(status_code=500, detail="Error force deleting document")

@router.get("/documents/status/{status}")
async def get_documents_by_status(
    status: str, 
    current_admin: TokenData = Depends(get_current_admin_user)
):
    """Get documents by processing status"""
    valid_statuses = ['pending', 'processing', 'completed', 'failed']
    
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    documents = AdminDocumentService.get_documents_by_status(status)
    return {"documents": documents, "count": len(documents)}

@router.get("/knowledge-base/stats")
async def get_knowledge_base_stats(current_admin: TokenData = Depends(get_current_admin_user)):
    """Get statistics about the global knowledge base"""
    try:
        from ..services.global_vector_store_manager import GlobalVectorStoreManager
        global_manager = GlobalVectorStoreManager()
        
        # Get comprehensive stats
        doc_summary = AdminDocumentService.get_documents_summary()
        global_stats = global_manager.get_global_store_stats()
        document_list = global_manager.get_document_list()
        
        return {
            "documents": doc_summary,
            "global_vector_store": global_stats,
            "active_documents": len(document_list),
            "document_list": document_list[:10],  # Show first 10 documents
            "status": "active" if global_stats['store_exists'] else "empty"
        }
    except Exception as e:
        logger.error(f"Error getting knowledge base stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching statistics")

@router.get("/vector-stores")
async def get_active_vector_stores(current_admin: TokenData = Depends(get_current_admin_user)):
    """Get all active documents in global knowledge base"""
    try:
        from ..services.global_vector_store_manager import GlobalVectorStoreManager
        global_manager = GlobalVectorStoreManager()
        
        document_list = global_manager.get_document_list()
        stats = global_manager.get_global_store_stats()
        
        return {
            "documents": document_list,
            "total_count": len(document_list),
            "global_stats": stats
        }
    except Exception as e:
        logger.error(f"Error fetching vector store documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching documents")

@router.post("/vector-store/rebuild")
async def rebuild_global_vector_store(
    background_tasks: BackgroundTasks,
    current_admin: TokenData = Depends(get_current_admin_user)
):
    """Rebuild the entire global vector store from active documents"""
    try:
        from ..services.global_vector_store_manager import GlobalVectorStoreManager
        global_manager = GlobalVectorStoreManager()
        
        # Get current stats before rebuild
        stats_before = global_manager.get_global_store_stats()
        
        # Perform rebuild
        success = global_manager.rebuild_entire_global_store()
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to rebuild global vector store")
        
        # Get stats after rebuild
        stats_after = global_manager.get_global_store_stats()
        
        # Clear all caches
        clear_global_cache()
        
        logger.info(f"Global vector store rebuilt by admin {current_admin.id}")
        
        return {
            "message": "Global vector store rebuilt successfully",
            "stats_before": stats_before,
            "stats_after": stats_after,
            "rebuild_success": success
        }
        
    except Exception as e:
        logger.error(f"Error rebuilding global vector store: {str(e)}")
        raise HTTPException(status_code=500, detail="Error rebuilding vector store")

@router.post("/cache/clear-global")
async def clear_global_document_cache(current_admin: TokenData = Depends(get_current_admin_user)):
    """Clear global document cache - useful after manual document changes"""
    try:
        clear_global_cache()
        logger.info(f"Global cache cleared manually by admin {current_admin.id}")
        return {"message": "Global cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing global cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Error clearing cache")
        logger.info(f"Global cache cleared manually by admin {current_admin.id}")
        return {"message": "Global cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing global cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Error clearing cache")