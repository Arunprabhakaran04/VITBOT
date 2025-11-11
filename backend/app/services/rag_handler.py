import os
from dotenv import load_dotenv
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from loguru import logger

# Load environment variables from .env file
load_dotenv()
from ...memory_cache import cache
from ...vector_store_db import get_user_vector_store_info
from .dual_embedding_manager import EmbeddingManager
from .admin_document_service import GlobalVectorStoreService
from .language_service import LanguageDetector
from .multilingual_vector_store_manager import MultilingualVectorStoreManager
from .enhanced_retrieval import create_enhanced_retriever
from .enhanced_retrieval import create_enhanced_retriever

_vector_store_cache = {}  # Keep in-memory cache as fallback

# Initialize language detector for query routing
_language_detector = LanguageDetector()
_multilingual_manager = MultilingualVectorStoreManager()

def load_global_vector_stores():
    """Load the single global vector store containing all admin documents"""
    try:
        # Check memory cache for global vector store
        global_cache_key = "global_vectorstore"
        cached_global = cache.get(global_cache_key)
        if cached_global:
            logger.debug("Using cached global vector store")
            return cached_global
        
        # Use the new GlobalVectorStoreManager
        from .global_vector_store_manager import GlobalVectorStoreManager
        global_manager = GlobalVectorStoreManager()
        
        # Ensure vector store consistency before loading
        consistency_check = global_manager.ensure_vector_store_consistency()
        if not consistency_check:
            logger.warning("Vector store consistency check failed, attempting to rebuild...")
            rebuild_success = global_manager._rebuild_global_store()
            if not rebuild_success:
                logger.error("Failed to rebuild global vector store")
                return None
        
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
        
        # Verify the loaded vector store has the expected number of vectors
        if vectorstore.index.ntotal != stats['total_vectors']:
            logger.warning(f"Mismatch detected: loaded {vectorstore.index.ntotal} vectors but stats show {stats['total_vectors']}")
            # Force rebuild and reload
            logger.info("Forcing rebuild due to mismatch...")
            rebuild_success = global_manager._rebuild_global_store()
            if rebuild_success:
                vectorstore = global_manager.get_vectorstore()
                logger.info(f"Reloaded after rebuild: {vectorstore.index.ntotal} vectors")
            else:
                logger.error("Rebuild failed")
                return None
        
        # Cache the global vector store (shorter cache time for more frequent updates)
        cache.set(global_cache_key, vectorstore, expire=1800)  # Cache for 30 minutes
        
        logger.info(f"Successfully loaded global vector store with {vectorstore.index.ntotal} total vectors from {stats['total_documents']} documents")
        
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
            cached_store = _vector_store_cache[combined_cache_key]
            logger.info(f"Using in-memory cached combined vector store for user {user_id} ({cached_store.index.ntotal} vectors)")
            return cached_store
        
        # Check memory cache second
        combined_redis_key = f"combined_vectorstore:user:{user_id}"
        cached_combined = cache.get(combined_redis_key)
        if cached_combined:
            logger.info(f"Using memory cached combined vector store for user {user_id}")
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
        
        # Load global/admin vector stores (this is the critical part)
        global_vectorstore = load_global_vector_stores()
        
        if not global_vectorstore:
            logger.warning(f"No global vector store available - this means no admin documents are processed")
            if user_vectorstore:
                logger.info(f"Using only user vector store for user {user_id}: {user_vectorstore.index.ntotal} vectors")
                combined_vectorstore = user_vectorstore
            else:
                logger.warning(f"No vector stores available for user {user_id}")
                return None
        else:
            # Combine vector stores
            if user_vectorstore:
                # User has documents + global documents
                logger.info(f"Combining user store ({user_vectorstore.index.ntotal} vectors) with global store ({global_vectorstore.index.ntotal} vectors)")
                combined_vectorstore = user_vectorstore
                combined_vectorstore.merge_from(global_vectorstore)
                total_vectors = combined_vectorstore.index.ntotal
                logger.info(f"Combined user + global vector stores for user {user_id}: {total_vectors} total vectors")
                
            else:
                # Only global documents (most common case for regular users)
                combined_vectorstore = global_vectorstore
                logger.info(f"Using only global vector stores for user {user_id}: {global_vectorstore.index.ntotal} vectors")
        
        if not combined_vectorstore:
            logger.error(f"Failed to create combined vector store for user {user_id}")
            return None
        
        # Cache the combined vector store
        _vector_store_cache[combined_cache_key] = combined_vectorstore
        cache.set(combined_redis_key, combined_vectorstore, expire=1800)  # Cache for 30 minutes
        
        logger.info(f"Successfully created and cached combined vector store for user {user_id} with {combined_vectorstore.index.ntotal} total vectors")
        
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
        logger.debug(f"Cleared old in-memory cache for user {user_id}")
    
    # Clear new combined cache
    combined_cache_key = f"combined_vectorstore_user_{user_id}"
    if combined_cache_key in _vector_store_cache:
        del _vector_store_cache[combined_cache_key]
        logger.debug(f"Cleared combined in-memory cache for user {user_id}")
    
    # Clear memory caches (pattern matching for user)
    cache.clear_user_data(user_id)
    logger.info(f"Cleared caches for user {user_id}")


def clear_global_cache():
    """Clear global vector store cache - call when admin documents change"""
    # Clear global cache from memory
    cache.delete("global_vectorstore")
    logger.info("Cleared global vector store cache")
    
    # Clear all user combined caches since they include global data
    global _vector_store_cache
    keys_to_remove = [key for key in _vector_store_cache.keys() if 'combined_vectorstore_user_' in key]
    for key in keys_to_remove:
        del _vector_store_cache[key]
    
    # Clear all combined caches from memory cache
    cleared_count = cache.clear_pattern("combined_vectorstore:user:*")
    
    # Also clear any old-style user caches that might exist
    cleared_count += cache.clear_pattern("vectorstore:user:*")
    
    logger.info(f"Cleared {len(keys_to_remove)} combined user caches due to global cache update")
    logger.info(f"Total cache entries cleared: {cleared_count}")
    
    # Force consistency check on next load
    cache.delete("global_store_consistency_checked")


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


def get_user_query_response(vectorstore, query, use_enhanced_retrieval=False):
    """
    Process user query with automatic language detection and namespace routing
    
    Args:
        vectorstore: FAISS vectorstore
        query: User query string
        use_enhanced_retrieval: If True, uses Fix 1 (Hybrid Search) + Fix 5 (Contextual Merging)
    """
    try:
        # Detect query language
        query_language, query_namespace = _multilingual_manager.detect_and_route(query)
        
        logger.info(f"Processing query in {query_language} (namespace: {query_namespace})")
        logger.info(f"Enhanced retrieval: {'ENABLED' if use_enhanced_retrieval else 'DISABLED'}")
        
        # Initialize LLM
        llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.1)
        
        # Choose retriever based on enhancement flag
        if use_enhanced_retrieval:
            # Use enhanced retriever with Hybrid Search + Contextual Merging
            try:
                enhanced_retriever = create_enhanced_retriever(
                    vectorstore=vectorstore,
                    enable_hybrid=True,  # Fix 1: Hybrid Search
                    enable_merging=True,  # Fix 5: Contextual Merging
                    enable_query_expansion=False  # Keep disabled for now
                )
                retriever = enhanced_retriever
                logger.info("Using ENHANCED retrieval (Hybrid Search + Contextual Merging)")
            except Exception as e:
                logger.warning(f"Enhanced retrieval failed, falling back to standard: {e}")
                retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
        else:
            # Standard FAISS retrieval
            retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
            logger.info("Using STANDARD FAISS retrieval")
        
        # Create retrieval chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm, 
            retriever=retriever,
            return_source_documents=True  # Enable source documents return
        )
        result = qa_chain.invoke(query)
        
        # Extract sources from the result
        sources = []
        if 'source_documents' in result and result['source_documents']:
            seen_sources = set()  # To avoid duplicate sources
            for doc in result['source_documents']:
                if hasattr(doc, 'metadata') and doc.metadata:
                    # Use filename if available (cleaner), otherwise extract from source path
                    document_name = doc.metadata.get('filename', 'Unknown Document')
                    if document_name == 'Unknown Document' and 'source' in doc.metadata:
                        # Extract filename from full path
                        import os
                        document_name = os.path.basename(doc.metadata['source'])
                    
                    # Get document language from metadata
                    doc_language = doc.metadata.get('language', 'unknown')
                    
                    # Use page_number (from enhanced chunker) instead of page
                    page_num = doc.metadata.get('page_number', doc.metadata.get('page', 'Unknown Page'))
                    
                    source_info = {
                        'document': document_name,
                        'page': page_num,
                        'chunk_index': doc.metadata.get('chunk_index', 1),
                        'language': doc_language
                    }
                    # Create a unique identifier for the source
                    source_key = f"{source_info['document']}-{source_info['page']}"
                    if source_key not in seen_sources:
                        sources.append(source_info)
                        seen_sources.add(source_key)
        
        logger.info(f"Query processed: found {len(sources)} source documents")
        logger.info(f"Query language: {query_language}, Sources languages: {set(s['language'] for s in sources)}")
        
        # Return both the answer and sources with language info
        return {
            'result': result.get('result', 'No answer found'),
            'sources': sources,
            'query_language': query_language,
            'query_namespace': query_namespace
        }
        
    except Exception as e:
        logger.error(f"Error in RAG query: {e}")
        raise e


def get_user_query_response_enhanced(vectorstore, query, 
                                    enable_hybrid: bool = True,
                                    enable_merging: bool = True,
                                    enable_query_expansion: bool = False):
    """
    Enhanced query processing with Hybrid Search (Fix 1) and Contextual Merging (Fix 5).
    
    Args:
        vectorstore: FAISS vector store
        query: User query
        enable_hybrid: Enable BM25 + FAISS hybrid search
        enable_merging: Enable contextual chunk merging
        enable_query_expansion: Enable query expansion (experimental)
        
    Returns:
        Dict with result, sources, and query metadata
    """
    try:
        # Detect query language
        query_language, query_namespace = _multilingual_manager.detect_and_route(query)
        
        logger.info(f"🔍 Enhanced RAG - Processing query in {query_language}")
        logger.info(f"   Hybrid Search: {enable_hybrid} | Merging: {enable_merging} | Expansion: {enable_query_expansion}")
        
        # Initialize LLM
        llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.1)
        
        # Create enhanced retriever
        enhanced_retriever = create_enhanced_retriever(
            vectorstore=vectorstore,
            documents=None,  # Will be extracted from vectorstore
            llm=llm if enable_query_expansion else None,
            enable_hybrid=enable_hybrid,
            enable_merging=enable_merging,
            enable_query_expansion=enable_query_expansion
        )
        
        # Get enhanced documents
        retrieved_docs = enhanced_retriever.get_relevant_documents(query, k=10)
        
        # Create QA chain with enhanced retrieval
        from langchain.chains.question_answering import load_qa_chain
        qa_chain = load_qa_chain(llm, chain_type="stuff")
        
        # Run QA with enhanced documents
        result = qa_chain.invoke({
            "input_documents": retrieved_docs,
            "question": query
        })
        
        # Extract sources from enhanced documents
        sources = []
        seen_sources = set()
        for doc in retrieved_docs:
            if hasattr(doc, 'metadata') and doc.metadata:
                # Use filename if available
                document_name = doc.metadata.get('filename', 'Unknown Document')
                if document_name == 'Unknown Document' and 'source' in doc.metadata:
                    import os
                    document_name = os.path.basename(doc.metadata['source'])
                
                doc_language = doc.metadata.get('language', 'unknown')
                page_num = doc.metadata.get('page_number', doc.metadata.get('page', 'Unknown Page'))
                
                # Check if this was a merged chunk
                merged_chunks = doc.metadata.get('merged_chunks', 1)
                chunk_range = doc.metadata.get('chunk_range', str(doc.metadata.get('chunk_index', 1)))
                
                source_info = {
                    'document': document_name,
                    'page': page_num,
                    'chunk_index': doc.metadata.get('chunk_index', 1),
                    'language': doc_language,
                    'merged_chunks': merged_chunks if merged_chunks > 1 else None,
                    'chunk_range': chunk_range if merged_chunks > 1 else None
                }
                
                source_key = f"{source_info['document']}-{source_info['page']}"
                if source_key not in seen_sources:
                    sources.append(source_info)
                    seen_sources.add(source_key)
        
        logger.info(f"✅ Enhanced query processed: {len(sources)} source documents")
        logger.info(f"   Merged chunks: {sum(1 for s in sources if s.get('merged_chunks'))}")
        
        return {
            'result': result.get('output_text', 'No answer found'),
            'sources': sources,
            'query_language': query_language,
            'query_namespace': query_namespace,
            'enhanced': True,
            'retrieval_stats': {
                'hybrid_search': enable_hybrid,
                'contextual_merging': enable_merging,
                'query_expansion': enable_query_expansion,
                'total_sources': len(sources),
                'merged_sources': sum(1 for s in sources if s.get('merged_chunks'))
            }
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced RAG query: {e}")
        # Fallback to standard retrieval
        logger.warning("Falling back to standard retrieval")
        return get_user_query_response(vectorstore, query)



def get_general_llm_response(query):
    try:
        llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.1)
        return llm.invoke(query).content
    except Exception as e:
        logger.error(f"Error in general LLM: {e}")
        raise e