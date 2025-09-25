import redis
import pickle
import json
import os
from typing import Any, Optional, Dict, List
from loguru import logger
from datetime import timedelta

class RedisCache:
    """Redis cache manager for the application"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(
            os.getenv("REDIS_CACHE_URL", os.getenv("REDIS_URL", "redis://localhost:6379/1")),  # Use DB 1 for cache (DB 0 for Celery)
            decode_responses=False  # Keep as bytes for pickle
        )
        
    def _prefix_key(self, key: str) -> str:
        """Add application prefix to all keys to prevent collisions with other applications"""
        app_prefix = os.getenv("REDIS_KEY_PREFIX", "social_api")
        return f"{app_prefix}:{key}"
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            prefixed_key = self._prefix_key(key)
            value = self.redis_client.get(prefixed_key)
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache with expiration (default 1 hour)"""
        try:
            prefixed_key = self._prefix_key(key)
            pickled_value = pickle.dumps(value)
            return self.redis_client.setex(prefixed_key, expire, pickled_value)
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            prefixed_key = self._prefix_key(key)
            return bool(self.redis_client.delete(prefixed_key))
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            prefixed_key = self._prefix_key(key)
            return bool(self.redis_client.exists(prefixed_key))
        except Exception as e:
            logger.error(f"Error checking cache existence: {e}")
            return False
    
    def get_json(self, key: str) -> Optional[Dict]:
        """Get JSON value from cache"""
        try:
            prefixed_key = self._prefix_key(key)
            value = self.redis_client.get(prefixed_key)
            if value:
                return json.loads(value.decode('utf-8'))
            return None
        except Exception as e:
            logger.error(f"Error getting JSON from cache: {e}")
            return None
    
    def set_json(self, key: str, value: Dict, expire: int = 3600) -> bool:
        """Set JSON value in cache"""
        try:
            prefixed_key = self._prefix_key(key)
            json_value = json.dumps(value)
            return self.redis_client.setex(prefixed_key, expire, json_value)
        except Exception as e:
            logger.error(f"Error setting JSON cache: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        try:
            prefixed_pattern = self._prefix_key(pattern)
            keys = self.redis_client.keys(prefixed_pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing pattern {pattern}: {e}")
            return 0
            
    def get_user_keys(self, user_id: int) -> List[str]:
        """Get all keys for a specific user"""
        try:
            user_pattern = self._prefix_key(f"*:user:{user_id}:*")
            keys = self.redis_client.keys(user_pattern)
            return [k.decode('utf-8') for k in keys] if keys else []
        except Exception as e:
            logger.error(f"Error getting user keys: {e}")
            return []
    
    def clear_user_data(self, user_id: int) -> int:
        """Clear all data for a specific user (for GDPR/privacy)"""
        try:
            user_keys = self.get_user_keys(user_id)
            if user_keys:
                return self.redis_client.delete(*user_keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing user data: {e}")
            return 0
    
    def get_cache_info(self) -> Dict:
        """Get cache statistics"""
        try:
            info = self.redis_client.info('memory')
            # Get all keys with our application prefix
            all_keys = self.redis_client.keys(self._prefix_key("*"))
            
            return {
                'used_memory': info.get('used_memory_human', 'N/A'),
                'total_keys': len(all_keys),
                'connected': True
            }
        except Exception as e:
            logger.error(f"Error getting cache info: {e}")
            return {'connected': False, 'error': str(e)}
            
    def health_check(self) -> bool:
        """Check if Redis is reachable and working"""
        try:
            return self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

# Global cache instance
cache = RedisCache()
