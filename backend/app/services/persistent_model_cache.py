"""
Persistent model cache using Redis for cross-process caching
"""

import pickle
import logging
import time
from typing import Optional, Literal
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

class PersistentModelCache:
    """Redis-based persistent cache for embedding models"""
    
    def __init__(self):
        try:
            # Import Redis cache from your existing setup
            from ....redis_cache import cache
            self.cache = cache
            self.cache_prefix = "embedding_model:"
            self.cache_timeout = 3600 * 24  # 24 hours
            logger.info("Initialized Persistent Model Cache with Redis")
        except Exception as e:
            logger.warning(f"Redis cache not available: {e}")
            self.cache = None
    
    def get_model_key(self, language: str) -> str:
        """Get Redis key for model"""
        return f"{self.cache_prefix}{language}"
    
    def get_cached_model(self, language: str) -> Optional[HuggingFaceEmbeddings]:
        """Get model from Redis cache"""
        if not self.cache:
            return None
            
        try:
            key = self.get_model_key(language)
            cached_data = self.cache.get(key)
            
            if cached_data:
                logger.info(f"⚡ Found {language} model in Redis cache")
                # Note: HuggingFaceEmbeddings objects can't be pickled directly
                # We'll need to recreate them, but this tells us it was cached
                return "CACHE_HIT"  # Signal that model should be recreated
            else:
                logger.info(f"❌ {language} model not found in Redis cache")
                return None
                
        except Exception as e:
            logger.error(f"Error getting model from cache: {e}")
            return None
    
    def cache_model(self, language: str, model_name: str):
        """Cache model metadata in Redis"""
        if not self.cache:
            return
            
        try:
            key = self.get_model_key(language)
            # Cache just the model name and metadata
            model_data = {
                'language': language,
                'model_name': model_name,
                'cached_at': time.time()
            }
            
            self.cache.set(key, model_data, expire=self.cache_timeout)
            logger.info(f"✅ Cached {language} model metadata in Redis")
            
        except Exception as e:
            logger.error(f"Error caching model: {e}")
    
    def clear_model_cache(self, language: str = None):
        """Clear cached models"""
        if not self.cache:
            return
            
        try:
            if language:
                key = self.get_model_key(language)
                self.cache.delete(key)
                logger.info(f"Cleared {language} model from cache")
            else:
                # Clear all model caches
                pattern = f"{self.cache_prefix}*"
                self.cache.clear_pattern(pattern)
                logger.info("Cleared all models from cache")
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")


# Global instance
_persistent_cache = PersistentModelCache()
