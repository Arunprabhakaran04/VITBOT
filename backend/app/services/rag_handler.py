import os
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from loguru import logger
from ...redis_cache import cache
from ...vector_store_db import get_user_vector_store_info
from .dual_embedding_manager import EmbeddingManager
from .admin_document_service import GlobalVectorStoreService

_vector_store_cache = {}  # Keep in-memory cache as fallback

def load_global_vector_stores():
    """Load the single global vector store containing all admin documents"""
    try:
        # Check Redis cache for global vector store
        global_cache_key = "global_vectorstore"
        cached_global = cache.get(global_cache_key)
        if cached_global:
            logger.info("Using Redis cached global vector store")
            return cached_global
        
        # Use the new GlobalVectorStoreManager
        from .global_vector_store_manager import GlobalVectorStoreManager
        global_manager = GlobalVectorStoreManager()
        
        # Check if global vector store exists
        stats = global_manager.get_global_store_stats()
        
        if not stats['store_exists'] or stats['total_vectors'] == 0:
            logger.info("No global vector store found or empty")
            return None
        
        # Load the global vector store using the new method
        vectorstore = global_manager.get_vectorstore()
        
        if not vectorstore or vectorstore.index.ntotal == 0:
            logger.info("Global vector store is empty")
            return None
        
        # Cache the global vector store
        cache.set(global_cache_key, vectorstore, expire=3600)  # Cache for 1 hour
        
        logger.success(f"Successfully loaded global vector store with {vectorstore.index.ntotal} total vectors from {stats['total_documents']} documents")
        
        return vectorstore
        
    except Exception as e:
        logger.error(f"Error loading global vector store: {e}")
        return None

def load_vectorstore_for_user(user_id: int):
    """Load vector store combining user documents and global admin documents"""
    try:
        # Check combined cache first
        combined_cache_key = f"combined_vectorstore_user_{user_id}"
        if combined_cache_key in _vector_store_cache:
            logger.info(f"Using in-memory cached combined vector store for user {user_id}")
            return _vector_store_cache[combined_cache_key]
        
        # Check Redis cache second
        combined_redis_key = f"combined_vectorstore:user:{user_id}"
        cached_combined = cache.get(combined_redis_key)
        if cached_combined:
            logger.info(f"Using Redis cached combined vector store for user {user_id}")
            _vector_store_cache[combined_cache_key] = cached_combined
            return cached_combined
        
        # Load user-specific vector store (if exists)
        user_vectorstore = None
        from ...database_connection import get_db_connection
        with get_db_connection() as conn:
            store_info = get_user_vector_store_info(conn, user_id)
        
        if store_info:
            vector_store_path = store_info['path']
            language = store_info['language']
            
            # Check if user vector store files exist
            index_file = os.path.join(vector_store_path, "index.faiss")
            pkl_file = os.path.join(vector_store_path, "index.pkl")
            
            if os.path.exists(index_file) and os.path.exists(pkl_file):
                embeddings = EmbeddingManager.get_embeddings_static()
                user_vectorstore = FAISS.load_local(
                    vector_store_path, 
                    embeddings, 
                    index_name="index", 
                    allow_dangerous_deserialization=True
                )
                logger.info(f"Loaded user vector store for user {user_id} with {user_vectorstore.index.ntotal} vectors")
        
        # Load global/admin vector stores
        global_vectorstore = load_global_vector_stores()
        
        # Combine vector stores
        if user_vectorstore and global_vectorstore:
            # User has documents + global documents
            combined_vectorstore = user_vectorstore
            combined_vectorstore.merge_from(global_vectorstore)
            total_vectors = combined_vectorstore.index.ntotal
            logger.success(f"Combined user + global vector stores for user {user_id}: {total_vectors} total vectors")
            
        elif global_vectorstore:
            # Only global documents (most common case for regular users)
            combined_vectorstore = global_vectorstore
            logger.info(f"Using only global vector stores for user {user_id}: {global_vectorstore.index.ntotal} vectors")
            
        elif user_vectorstore:
            # Only user documents (fallback)
            combined_vectorstore = user_vectorstore
            logger.info(f"Using only user vector store for user {user_id}: {user_vectorstore.index.ntotal} vectors")
            
        else:
            # No documents available
            logger.warning(f"No vector stores available for user {user_id}")
            return None
        
        # Cache the combined vector store
        _vector_store_cache[combined_cache_key] = combined_vectorstore
        cache.set(combined_redis_key, combined_vectorstore, expire=1800)  # Cache for 30 minutes
        
        return combined_vectorstore
        
    except Exception as e:
        logger.error(f"Error loading combined vector store for user {user_id}: {e}")
        # Clear cache on error
        combined_cache_key = f"combined_vectorstore_user_{user_id}"
        if combined_cache_key in _vector_store_cache:
            del _vector_store_cache[combined_cache_key]
        cache.delete(f"combined_vectorstore:user:{user_id}")
        return None


def clear_user_cache(user_id: int):
    """Clear the vector store cache for a specific user"""
    # Clear old user-specific cache
    cache_key = f"vectorstore_user_{user_id}"
    if cache_key in _vector_store_cache:
        del _vector_store_cache[cache_key]
        logger.info(f"Cleared old in-memory cache for user {user_id}")
    
    # Clear new combined cache
    combined_cache_key = f"combined_vectorstore_user_{user_id}"
    if combined_cache_key in _vector_store_cache:
        del _vector_store_cache[combined_cache_key]
        logger.info(f"Cleared combined in-memory cache for user {user_id}")
    
    # Clear Redis caches
    cache.delete(f"vectorstore:user:{user_id}")
    cache.delete(f"combined_vectorstore:user:{user_id}")
    logger.info(f"Cleared Redis caches for user {user_id}")


def clear_global_cache():
    """Clear global vector store cache - call when admin documents change"""
    # Clear global cache from Redis
    cache.delete("global_vectorstore")
    logger.info("Cleared global vector store cache")
    
    # Clear all user combined caches since they include global data
    global _vector_store_cache
    keys_to_remove = [key for key in _vector_store_cache.keys() if 'combined_vectorstore_user_' in key]
    for key in keys_to_remove:
        del _vector_store_cache[key]
    
    # Clear all combined caches from Redis
    cache.clear_pattern("combined_vectorstore:user:*")
    logger.info(f"Cleared {len(keys_to_remove)} combined user caches due to global cache update")


def clear_all_cache():
    """Clear all vector store cache - useful for maintenance"""
    global _vector_store_cache
    cache_size = len(_vector_store_cache)
    _vector_store_cache = {}
    
    # Clear all vectorstore keys from Redis
    cleared_count = 0
    cleared_count += cache.clear_pattern("vectorstore:user:*")
    cleared_count += cache.clear_pattern("combined_vectorstore:user:*")
    cleared_count += 1 if cache.delete("global_vectorstore") else 0
    
    logger.info(f"Cleared all cache - {cache_size} in-memory entries and {cleared_count} Redis entries removed")


def get_cache_info():
    """Get information about current cache state"""
    redis_info = cache.get_cache_info()
    in_memory_users = []
    combined_users = []
    
    for key in _vector_store_cache.keys():
        if key.startswith("vectorstore_user_"):
            in_memory_users.append(key.replace("vectorstore_user_", ""))
        elif key.startswith("combined_vectorstore_user_"):
            combined_users.append(key.replace("combined_vectorstore_user_", ""))
    
    return {
        "in_memory": {
            "legacy_cached_users": in_memory_users,
            "combined_cached_users": combined_users,
            "total_cache_size": len(_vector_store_cache)
        },
        "redis": redis_info
    }


def get_user_query_response(vectorstore, query):
    try:
        llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.1)
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm, 
            retriever=vectorstore.as_retriever(search_kwargs={"k": 4}),
            return_source_documents=True  # Enable source documents return
        )
        result = qa_chain.invoke(query)
        
        # Extract sources from the result
        sources = []
        if 'source_documents' in result and result['source_documents']:
            seen_sources = set()  # To avoid duplicate sources
            for doc in result['source_documents']:
                if hasattr(doc, 'metadata') and doc.metadata:
                    source_info = {
                        'document': doc.metadata.get('source', 'Unknown Document'),
                        'page': doc.metadata.get('page', 'Unknown Page'),
                        'chunk_index': doc.metadata.get('chunk_index', 1)
                    }
                    # Create a unique identifier for the source
                    source_key = f"{source_info['document']}-{source_info['page']}"
                    if source_key not in seen_sources:
                        sources.append(source_info)
                        seen_sources.add(source_key)
        
        # Return both the answer and sources
        return {
            'result': result.get('result', 'No answer found'),
            'sources': sources
        }
        
    except Exception as e:
        logger.error(f"Error in RAG query: {e}")
        raise e


def get_general_llm_response(query):
    try:
        llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.1)
        return llm.invoke(query).content
    except Exception as e:
        logger.error(f"Error in general LLM: {e}")
        raise e