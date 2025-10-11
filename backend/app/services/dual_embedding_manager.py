from langchain_huggingface import HuggingFaceEmbeddings
import logging

logger = logging.getLogger(__name__)

# Global cache for embedding models - shared across ALL instances
_GLOBAL_EMBEDDING_CACHE = {}

class EmbeddingManager:
    """
    Manages English embedding model with global caching
    English: BAAI/bge-small-en-v1.5
    """
    
    MODEL = "BAAI/bge-small-en-v1.5"
    
    def __init__(self):
        # No instance-level cache - use global cache only
        logger.info("Initialized Embedding Manager")
    
    @classmethod
    def _check_memory_cache(cls) -> bool:
        """Check if model exists in memory cache"""
        try:
            from ...memory_cache import cache
            key = f"embedding_model_loaded:english"
            cached = cache.get(key)
            if cached:
                logger.info(f"English model was previously loaded in another process")
                return True
            return False
        except Exception as e:
            logger.debug(f"Memory cache check failed: {e}")
            return False
    
    @classmethod
    def _mark_memory_cache(cls):
        """Mark model as loaded in memory cache"""
        try:
            from ...memory_cache import cache
            key = f"embedding_model_loaded:english"
            cache.set(key, True, expire=3600 * 24)  # 24 hours
            logger.info(f"Marked English model as loaded in memory cache")
        except Exception as e:
            logger.debug(f"Memory cache marking failed: {e}")

    @classmethod
    def get_embeddings_static(cls) -> HuggingFaceEmbeddings:
        """
        Class method to get English embedding model with Redis awareness
        Model is cached globally after first load for maximum performance
        """
        global _GLOBAL_EMBEDDING_CACHE
        
        # Return cached model if available (GLOBAL CACHE)
        if 'english' in _GLOBAL_EMBEDDING_CACHE:
            logger.info(f"Using globally cached English embedding model")
            return _GLOBAL_EMBEDDING_CACHE['english']
        
        # Check if model was loaded in another process (MEMORY CACHE AWARENESS)
        model_name = cls.MODEL
        if cls._check_memory_cache():
            logger.info(f"English model exists in another process, loading to this process...")
        else:
            logger.info(f"Loading English embedding model: {model_name} (first time across all processes)")
        
        try:
            embedding_model = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True}
            )
            
            # Cache the model GLOBALLY
            _GLOBAL_EMBEDDING_CACHE['english'] = embedding_model
            
            # Mark as loaded in memory cache for other processes
            cls._mark_memory_cache()
            
            logger.info(f"English embedding model loaded and cached globally")
            logger.info(f"Global cache now contains: {list(_GLOBAL_EMBEDDING_CACHE.keys())}")
            
            return embedding_model
            
        except Exception as e:
            logger.error(f"Failed to load English embedding model {model_name}: {e}")
            raise e
    
    def get_embeddings(self) -> HuggingFaceEmbeddings:
        """Instance method that calls the class method for backward compatibility"""
        return self.__class__.get_embeddings_static()
    
    @classmethod
    def get_model_info(cls) -> dict:
        """
        Get information about the embedding model
        """
        global _GLOBAL_EMBEDDING_CACHE
        return {
            'language': 'english',
            'model_name': cls.MODEL,
            'is_cached': 'english' in _GLOBAL_EMBEDDING_CACHE,
            'global_cache_size': len(_GLOBAL_EMBEDDING_CACHE)
        }
    
    @classmethod
    def clear_cache(cls):
        """
        Clear all cached models to free memory
        """
        global _GLOBAL_EMBEDDING_CACHE
        cache_size = len(_GLOBAL_EMBEDDING_CACHE)
        _GLOBAL_EMBEDDING_CACHE.clear()
        logger.info(f"Cleared global embedding model cache ({cache_size} models removed)")
    
    @classmethod
    def preload_model(cls):
        """
        Preload the English model for faster access
        """
        logger.info("Preloading English embedding model...")
        cls.get_embeddings_static()
        logger.info("English embedding model preloaded and cached globally")
    
    @classmethod
    def get_cache_status(cls) -> dict:
        """
        Get current global cache status
        """
        global _GLOBAL_EMBEDDING_CACHE
        return {
            'cached_languages': list(_GLOBAL_EMBEDDING_CACHE.keys()),
            'total_cached': len(_GLOBAL_EMBEDDING_CACHE),
            'available_model': cls.MODEL
        }
