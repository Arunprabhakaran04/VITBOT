"""
Enhanced Chat Router with Role-Based Access Control
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
from loguru import logger

from ...oauth2 import get_current_user
from ...schemas import TokenData
from ..services.rag_handler import get_user_query_response, get_general_llm_response, clear_user_cache, get_cache_info
from ..services.chat_db_service import ChatDBService
from ..services.rag_service import DocumentProcessor
from ..services.chat_cache import ChatCache
from ..services.admin_document_service import GlobalVectorStoreService

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class ChatRequest(BaseModel):
    query: str
    chat_id: Optional[str] = None
    has_pdf: bool = False

class ChatTitleUpdate(BaseModel):
    title: str

def load_global_vectorstore_for_users():
    """Load global vector store from admin documents for regular users"""
    try:
        active_stores = GlobalVectorStoreService.get_active_vector_stores()
        
        if not active_stores:
            logger.warning("No active admin documents found for global knowledge base")
            return None
            
        # For now, we'll combine all vector stores into one
        # In a more advanced implementation, you might want to merge them
        # or search across multiple stores
        
        processor = DocumentProcessor()
        
        # Load the first available vector store as primary
        # This is a simplified implementation - in production you might want
        # to merge multiple vector stores or implement a more sophisticated approach
        primary_store = active_stores[0]
        vector_store_path = primary_store['vector_store_path']
        
        if os.path.exists(os.path.join(vector_store_path, "index.faiss")):
            from langchain_community.vectorstores import FAISS
            from ..services.dual_embedding_manager import EmbeddingManager
            
            embedding_manager = EmbeddingManager()
            vectorstore = FAISS.load_local(
                vector_store_path, 
                embedding_manager.get_embeddings(), 
                index_name="index",
                allow_dangerous_deserialization=True
            )
            
            logger.info(f"Loaded global vector store with {vectorstore.index.ntotal} vectors from admin documents")
            return vectorstore
        else:
            logger.warning(f"Vector store files not found at: {vector_store_path}")
            return None
            
    except Exception as e:
        logger.error(f"Error loading global vector store: {str(e)}")
        return None

def load_admin_vectorstore_for_admin(admin_id: int):
    """Load vector store for admin users (includes their personal uploads)"""
    try:
        # For admins, we can load both their personal uploads and global knowledge
        # For now, let's use the same global approach
        return load_global_vectorstore_for_users()
    except Exception as e:
        logger.error(f"Error loading admin vector store: {str(e)}")
        return None

@router.post("/chat")
async def chat_with_rag(request: Request, data: ChatRequest, current_user: TokenData = Depends(get_current_user)):
    logger.info(f"Chat request from {current_user.role} user {current_user.email}")
    logger.debug(f"Request data: {data}")
    
    # Role-based access control
    if current_user.role == 'user':
        # Regular users can ONLY do PDF-based inference
        if not data.has_pdf:
            raise HTTPException(
                status_code=403, 
                detail="Regular users can only perform PDF-based queries. General AI chat is restricted to admins."
            )
        
        logger.info("Regular user performing PDF-based query")
    elif current_user.role == 'admin':
        logger.info("Admin user - full access granted")
    else:
        raise HTTPException(status_code=403, detail="Invalid user role")
    
    try:
        # Check cache first for identical queries
        cached_response = ChatCache.get_cached_response(current_user.id, data.query, data.has_pdf)
        if cached_response:
            logger.info("Returning cached response")
            
            # Still save to chat history if chat_id provided
            if data.chat_id:
                chat_info = ChatDBService.create_or_get_chat(current_user.id, data.chat_id, data.query)
                ChatDBService.save_message(data.chat_id, "user", data.query)
                ChatDBService.save_message(data.chat_id, "assistant", cached_response["response"], cached_response["source"])
            
            # Prepare cached response
            response_data = {
                "response": cached_response["response"], 
                "source": cached_response["source"],
                "cached": True
            }
            
            # Add sources if available in cached response
            if "sources" in cached_response:
                response_data["sources"] = cached_response["sources"]
            
            return response_data
        
        # Create or get chat record
        if data.chat_id:
            chat_info = ChatDBService.create_or_get_chat(current_user.id, data.chat_id, data.query)
        
        # Save user message
        if data.chat_id:
            ChatDBService.save_message(data.chat_id, "user", data.query)
        
        # Get AI response based on request type and user role
        sources = []
        
        if not data.has_pdf:
            # Only admins can use general LLM
            if current_user.role != 'admin':
                raise HTTPException(
                    status_code=403, 
                    detail="General AI chat is restricted to admin users"
                )
            
            logger.info("Admin using general LLM response")
            response = get_general_llm_response(data.query)
            source = "general"
            
        else:
            logger.info("Attempting to use global knowledge base")
            
            # Load appropriate vector store based on user role
            if current_user.role == 'admin':
                vectorstore = load_admin_vectorstore_for_admin(current_user.id)
            else:
                vectorstore = load_global_vectorstore_for_users()
            
            if vectorstore is None:
                if current_user.role == 'admin':
                    # Admins can fall back to general LLM
                    logger.warning("No vector store found for admin, falling back to general LLM")
                    response = get_general_llm_response(data.query)
                    source = "general"
                else:
                    # Regular users get an error
                    raise HTTPException(
                        status_code=404, 
                        detail="No documents available for querying. Please contact an administrator to upload documents."
                    )
            else:
                logger.success("Using global knowledge base for response")
                rag_response = get_user_query_response(vectorstore, data.query)
                response = rag_response.get('result') if isinstance(rag_response, dict) else rag_response
                sources = rag_response.get('sources', []) if isinstance(rag_response, dict) else []
                source = "rag"
        
        # Handle response format for backward compatibility
        if isinstance(response, dict):
            response = response.get("result") or next((v for v in response.values() if isinstance(v, str)), "[No response]")
        
        # Cache the response for future identical queries
        ChatCache.cache_response(current_user.id, data.query, data.has_pdf, response, source, sources)
        
        # Save assistant message
        if data.chat_id:
            ChatDBService.save_message(data.chat_id, "assistant", response, source)
        
        logger.success(f"Chat response sent (source: {source}, role: {current_user.role})")
        
        # Prepare response with sources if available
        response_data = {
            "response": response, 
            "source": source, 
            "user_role": current_user.role,
            "cached": False
        }
        
        if sources:
            response_data["sources"] = sources
        
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions (like permission errors)
        raise
    except Exception as e:
        logger.error(f"Error in chat processing: {str(e)}")
        logger.exception("Full chat error traceback:")
        raise HTTPException(status_code=500, detail="Error processing chat request")

@router.get("/list_chats")
async def list_user_chats(current_user: TokenData = Depends(get_current_user)):
    """Get all chats for the current user"""
    try:
        chats = ChatDBService.get_user_chats(current_user.id)
        logger.info(f"Retrieved {len(chats)} chats for user {current_user.email}")
        
        return {
            "chats": chats,
            "count": len(chats),
            "user_role": current_user.role
        }
    except Exception as e:
        logger.error(f"Error retrieving chats: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving chats")

@router.get("/chat_history/{chat_id}")
async def get_chat_history(chat_id: str, current_user: TokenData = Depends(get_current_user)):
    """Get chat history for a specific chat"""
    try:
        messages = ChatDBService.get_chat_messages(chat_id, current_user.id)
        logger.info(f"Retrieved {len(messages)} messages for chat {chat_id}")
        
        return {
            "chat_id": chat_id,
            "messages": messages,
            "count": len(messages),
            "user_role": current_user.role
        }
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        if "access denied" in str(e).lower():
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail="Error retrieving chat history")

@router.delete("/chat/{chat_id}")
async def delete_chat(chat_id: str, current_user: TokenData = Depends(get_current_user)):
    """Delete a chat"""
    try:
        success = ChatDBService.delete_chat(chat_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        logger.info(f"Deleted chat {chat_id} for user {current_user.email}")
        return {"message": "Chat deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting chat")

@router.put("/chat/{chat_id}/title")
async def update_chat_title(
    chat_id: str, 
    title_data: ChatTitleUpdate, 
    current_user: TokenData = Depends(get_current_user)
):
    """Update chat title"""
    try:
        success = ChatDBService.update_chat_title(chat_id, current_user.id, title_data.title)
        if not success:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        logger.info(f"Updated title for chat {chat_id}")
        return {"message": "Chat title updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chat title: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating chat title")

@router.post("/clear_cache")
async def clear_cache(current_user: TokenData = Depends(get_current_user)):
    """Clear cache for current user"""
    try:
        # Only admins can clear cache completely
        if current_user.role == 'admin':
            cleared = clear_user_cache(current_user.id)
            ChatCache.clear_user_chat_cache(current_user.id)
        else:
            # Regular users can only clear their chat cache
            cleared = ChatCache.clear_user_chat_cache(current_user.id)
        
        logger.info(f"Cleared cache for {current_user.role} user {current_user.email}")
        return {"message": "Cache cleared successfully", "user_role": current_user.role}
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Error clearing cache")

@router.post("/clear_pdf")
async def clear_pdf(current_user: TokenData = Depends(get_current_user)):
    """Clear PDF data - Admin only function"""
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=403, 
            detail="PDF management is restricted to admin users"
        )
    
    try:
        logger.info(f"Admin clearing PDF data for user {current_user.id}")
        
        # Clear the in-memory cache
        clear_user_cache(current_user.id)
        
        # For admin users, we might want to clear their personal vector stores
        # but keep the global knowledge base intact
        processor = DocumentProcessor()
        user_vector_dir = os.path.join(processor.vector_store_dir, f"user_{current_user.id}")
        if os.path.exists(user_vector_dir):
            import shutil
            shutil.rmtree(user_vector_dir)
            logger.info(f"Cleaned up personal vector store for admin {current_user.id}")
        
        logger.success(f"PDF data cleared successfully for admin {current_user.id}")
        return {"message": "PDF data cleared successfully", "user_role": current_user.role}
    except Exception as e:
        logger.error(f"Error clearing PDF data: {str(e)}")
        raise HTTPException(status_code=500, detail="Error clearing PDF data")

@router.get("/user_cache_data")
async def get_user_cache_data(current_user: TokenData = Depends(get_current_user)):
    """Get cache information for current user"""
    from ...redis_cache import cache
    
    try:
        user_keys = cache.get_user_keys(current_user.id)
        
        return {
            "user_id": current_user.id,
            "user_role": current_user.role,
            "total_keys": len(user_keys),
            "key_samples": user_keys[:10] if len(user_keys) > 10 else user_keys
        }
    except Exception as e:
        logger.error(f"Error getting cache data: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving cache data")

@router.get("/knowledge_base_status")
async def get_knowledge_base_status(current_user: TokenData = Depends(get_current_user)):
    """Get status of available knowledge base"""
    try:
        active_stores = GlobalVectorStoreService.get_active_vector_stores()
        kb_stats = GlobalVectorStoreService.get_global_knowledge_stats()
        
        return {
            "available_documents": len(active_stores),
            "total_chunks": kb_stats.get('total_chunks', 0),
            "languages": kb_stats.get('languages_count', 0),
            "status": "active" if active_stores else "empty",
            "user_role": current_user.role,
            "can_upload": current_user.role == 'admin',
            "can_query": len(active_stores) > 0
        }
    except Exception as e:
        logger.error(f"Error getting knowledge base status: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving knowledge base status")

@router.get("/knowledge_base_documents")
async def get_knowledge_base_documents(current_user: TokenData = Depends(get_current_user)):
    """Get list of available documents in knowledge base for regular users"""
    try:
        # Get all completed admin documents (since we have a single global store)
        from ..services.admin_document_service import AdminDocumentService
        completed_docs = AdminDocumentService.get_completed_documents()
        
        # Transform admin document data into user-friendly format
        documents = []
        for doc in completed_docs:
            documents.append({
                "id": doc["id"],
                "original_filename": doc["original_filename"], 
                "language": doc.get("language", "english"),
                "created_at": doc.get("created_at"),
                "processing_status": "completed",
                "is_active": True,
                "file_size": None  # Don't expose file size to regular users
            })
        
        return {
            "documents": documents,
            "total_count": len(documents),
            "user_can_access": True,
            "message": f"Found {len(documents)} documents available for querying"
        }
    except Exception as e:
        logger.error(f"Error getting knowledge base documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving knowledge base documents")