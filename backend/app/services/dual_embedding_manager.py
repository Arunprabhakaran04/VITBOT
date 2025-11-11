from langchain_huggingface import HuggingFaceEmbeddings
import logging

logger = logging.getLogger(__name__)

# Global cache for embedding models - shared across ALL instances
_GLOBAL_EMBEDDING_CACHE = {}

class EmbeddingManager:
    """
    Manages both English and Multilingual embedding models with global caching
    English: BAAI/bge-small-en-v1.5 (384 dimensions)
    Multilingual: intfloat/multilingual-e5-large (1024 dimensions)
    """
    
    # Model configurations
    ENGLISH_MODEL = "BAAI/bge-small-en-v1.5"
    MULTILINGUAL_MODEL = "intfloat/multilingual-e5-large"
    
    # Dimension mapping
    ENGLISH_DIMENSIONS = 384
    MULTILINGUAL_DIMENSIONS = 1024
    
    # Legacy compatibility
    MODEL = ENGLISH_MODEL
    
    def __init__(self):
        # No instance-level cache - use global cache only
        logger.info("Initialized Multilingual Embedding Manager")
    
    @classmethod
    def _check_memory_cache(cls, language: str) -> bool:
        """Check if model exists in memory cache"""
        try:
            from ...memory_cache import cache
            key = f"embedding_model_loaded:{language}"
            cached = cache.get(key)
            if cached:
                logger.info(f"{language.title()} model was previously loaded in another process")
                return True
            return False
        except Exception as e:
            logger.debug(f"Memory cache check failed: {e}")
            return False
    
    @classmethod
    def _mark_memory_cache(cls, language: str):
        """Mark model as loaded in memory cache"""
        try:
            from ...memory_cache import cache
            key = f"embedding_model_loaded:{language}"
            cache.set(key, True, expire=3600 * 24)  # 24 hours
            logger.info(f"Marked {language.title()} model as loaded in memory cache")
        except Exception as e:
            logger.debug(f"Memory cache marking failed: {e}")

    @classmethod
    def get_embeddings_static(cls, language: str = 'english') -> HuggingFaceEmbeddings:
        """
        Class method to get embedding model based on language with Redis awareness
        Model is cached globally after first load for maximum performance
        
        Args:
            language: 'english' or 'multilingual'
        """
        global _GLOBAL_EMBEDDING_CACHE
        
        # Validate language
        if language not in ['english', 'multilingual']:
            logger.warning(f"Invalid language '{language}', defaulting to 'english'")
            language = 'english'
        
        # Return cached model if available (GLOBAL CACHE)
        if language in _GLOBAL_EMBEDDING_CACHE:
            logger.info(f"Using globally cached {language.title()} embedding model")
            return _GLOBAL_EMBEDDING_CACHE[language]
        
        # Select model based on language
        model_name = cls.ENGLISH_MODEL if language == 'english' else cls.MULTILINGUAL_MODEL
        
        # Check if model was loaded in another process (MEMORY CACHE AWARENESS)
        if cls._check_memory_cache(language):
            logger.info(f"{language.title()} model exists in another process, loading to this process...")
        else:
            logger.info(f"Loading {language.title()} embedding model: {model_name} (first time across all processes)")
        
        try:
            embedding_model = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True}
            )
            
            # Cache the model GLOBALLY
            _GLOBAL_EMBEDDING_CACHE[language] = embedding_model
            
            # Mark as loaded in memory cache for other processes
            cls._mark_memory_cache(language)
            
            dimension = cls.ENGLISH_DIMENSIONS if language == 'english' else cls.MULTILINGUAL_DIMENSIONS
            logger.info(f"{language.title()} embedding model loaded and cached globally ({dimension}D)")
            logger.info(f"Global cache now contains: {list(_GLOBAL_EMBEDDING_CACHE.keys())}")
            
            return embedding_model
            
        except Exception as e:
            logger.error(f"Failed to load {language.title()} embedding model {model_name}: {e}")
            raise e
    
    def get_embeddings(self, language: str = 'english') -> HuggingFaceEmbeddings:
        """Instance method that calls the class method for backward compatibility"""
        return self.__class__.get_embeddings_static(language)
    
    @classmethod
    def get_model_for_language(cls, language: str) -> HuggingFaceEmbeddings:
        """
        Get the appropriate embedding model for the detected language
        
        Args:
            language: Detected language code (e.g., 'english', 'tamil', 'hindi', 'telugu', etc.)
        
        Returns:
            HuggingFaceEmbeddings model
        """
        # Map languages to model types
        if language.lower() in ['english', 'en']:
            return cls.get_embeddings_static('english')
        else:
            # All non-English languages use multilingual model
            return cls.get_embeddings_static('multilingual')
    
    @classmethod
    def get_namespace_for_language(cls, language: str) -> str:
        """
        Get the namespace identifier for vector store based on language
        
        Args:
            language: Detected language code
        
        Returns:
            Namespace string ('english_docs' or 'multilingual_docs')
        """
        if language.lower() in ['english', 'en']:
            return 'english_docs'
        else:
            return 'multilingual_docs'
    
    @classmethod
    def get_model_info(cls, language: str = 'english') -> dict:
        """
        Get information about the embedding model
        """
        global _GLOBAL_EMBEDDING_CACHE
        
        model_name = cls.ENGLISH_MODEL if language == 'english' else cls.MULTILINGUAL_MODEL
        dimensions = cls.ENGLISH_DIMENSIONS if language == 'english' else cls.MULTILINGUAL_DIMENSIONS
        
        return {
            'language': language,
            'model_name': model_name,
            'dimensions': dimensions,
            'is_cached': language in _GLOBAL_EMBEDDING_CACHE,
            'global_cache_size': len(_GLOBAL_EMBEDDING_CACHE)
        }
    
    @classmethod
    def clear_cache(cls, language: str = None):
        """
        Clear cached models to free memory
        
        Args:
            language: Specific language to clear, or None to clear all
        """
        global _GLOBAL_EMBEDDING_CACHE
        
        if language:
            if language in _GLOBAL_EMBEDDING_CACHE:
                del _GLOBAL_EMBEDDING_CACHE[language]
                logger.info(f"Cleared {language.title()} embedding model from cache")
        else:
            cache_size = len(_GLOBAL_EMBEDDING_CACHE)
            _GLOBAL_EMBEDDING_CACHE.clear()
            logger.info(f"Cleared global embedding model cache ({cache_size} models removed)")
    
    @classmethod
    def preload_models(cls, languages: list = None):
        """
        Preload embedding models for faster access
        
        Args:
            languages: List of languages to preload ['english', 'multilingual'], or None for both
        """
        if languages is None:
            languages = ['english', 'multilingual']
        
        for lang in languages:
            logger.info(f"Preloading {lang.title()} embedding model...")
            cls.get_embeddings_static(lang)
            logger.info(f"{lang.title()} embedding model preloaded and cached globally")
    
    @classmethod
    def get_cache_status(cls) -> dict:
        """
        Get current global cache status
        """
        global _GLOBAL_EMBEDDING_CACHE
        
        cached_models = {}
        for lang in _GLOBAL_EMBEDDING_CACHE.keys():
            model_name = cls.ENGLISH_MODEL if lang == 'english' else cls.MULTILINGUAL_MODEL
            dimensions = cls.ENGLISH_DIMENSIONS if lang == 'english' else cls.MULTILINGUAL_DIMENSIONS
            cached_models[lang] = {
                'model': model_name,
                'dimensions': dimensions
            }
        
        return {
            'cached_languages': list(_GLOBAL_EMBEDDING_CACHE.keys()),
            'total_cached': len(_GLOBAL_EMBEDDING_CACHE),
            'models': cached_models,
            'available_models': {
                'english': {'model': cls.ENGLISH_MODEL, 'dimensions': cls.ENGLISH_DIMENSIONS},
                'multilingual': {'model': cls.MULTILINGUAL_MODEL, 'dimensions': cls.MULTILINGUAL_DIMENSIONS}
            }
        }
