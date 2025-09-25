import os
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from loguru import logger
from ...redis_cache import cache
from ...vector_store_db import get_user_vector_store_info
from .dual_embedding_manager import EmbeddingManager

_vector_store_cache = {}  # Keep in-memory cache as fallback

def load_vectorstore_for_user(user_id: int):
    """Load vector store with English embedding model"""
    try:
        # Check in-memory cache first (fastest)
        cache_key = f"vectorstore_user_{user_id}"
        if cache_key in _vector_store_cache:
            logger.info(f"Using in-memory cached vector store for user {user_id}")
            return _vector_store_cache[cache_key]
        
        # Check Redis cache second (persistent across restarts)
        redis_key = f"vectorstore:user:{user_id}"
        cached_vectorstore = cache.get(redis_key)
        if cached_vectorstore:
            logger.info(f"Using Redis cached vector store for user {user_id}")
            _vector_store_cache[cache_key] = cached_vectorstore  # Also cache in memory
            return cached_vectorstore
        
        # Load from disk if not in cache
        from ...database_connection import get_db_connection
        with get_db_connection() as conn:
            store_info = get_user_vector_store_info(conn, user_id)
        
        if not store_info:
            logger.warning(f"No vector store found for user {user_id}")
            return None
            
        vector_store_path = store_info['path']
        language = store_info['language']
        embedding_model_name = store_info['embedding_model']
        
        logger.info(f"Loading {language} vector store from disk: {vector_store_path}")
        logger.info(f"Using embedding model: {embedding_model_name}")
        
        # Check if vector store files exist
        index_file = os.path.join(vector_store_path, "index.faiss")
        pkl_file = os.path.join(vector_store_path, "index.pkl")
        
        if not os.path.exists(index_file) or not os.path.exists(pkl_file):
            logger.warning(f"Vector store files not found for user {user_id}")
            return None
        
        # Get English embedding model (only model we support now)
        embeddings = EmbeddingManager.get_embeddings_static()

        # Load the vector store
        vectorstore = FAISS.load_local(
            vector_store_path, 
            embeddings, 
            index_name="index", 
            allow_dangerous_deserialization=True
        )
        
        # Cache in both Redis and memory
        _vector_store_cache[cache_key] = vectorstore
        cache.set(redis_key, vectorstore, expire=3600)  # Cache for 1 hour
        
        logger.info(f"Loaded and cached {language} vector store for user {user_id} with {vectorstore.index.ntotal} vectors")
        return vectorstore
        
    except Exception as e:
        logger.error(f"Error loading vector store for user {user_id}: {e}")
        # Clear the cache entries if loading fails
        cache_key = f"vectorstore_user_{user_id}"
        if cache_key in _vector_store_cache:
            del _vector_store_cache[cache_key]
        cache.delete(f"vectorstore:user:{user_id}")
        return None


def clear_user_cache(user_id: int):
    """Clear the vector store cache for a specific user"""
    # Clear in-memory cache
    cache_key = f"vectorstore_user_{user_id}"
    if cache_key in _vector_store_cache:
        del _vector_store_cache[cache_key]
        logger.info(f"Cleared in-memory cache for user {user_id}")
    
    # Clear Redis cache
    redis_key = f"vectorstore:user:{user_id}"
    cache.delete(redis_key)
    logger.info(f"Cleared Redis cache for user {user_id}")


def clear_all_cache():
    """Clear all vector store cache - useful for maintenance"""
    global _vector_store_cache
    cache_size = len(_vector_store_cache)
    _vector_store_cache = {}
    
    # Clear all vectorstore keys from Redis
    cleared_count = cache.clear_pattern("vectorstore:user:*")
    
    logger.info(f"Cleared all cache - {cache_size} in-memory entries and {cleared_count} Redis entries removed")


def get_cache_info():
    """Get information about current cache state"""
    redis_info = cache.get_cache_info()
    in_memory_users = [key.replace("vectorstore_user_", "") for key in _vector_store_cache.keys()]
    
    return {
        "in_memory": {
            "cached_users": in_memory_users,
            "cache_size": len(_vector_store_cache)
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