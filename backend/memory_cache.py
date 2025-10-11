"""
In-Memory Cache - Simple replacement for Redis
Production-ready with proper memory management
"""
import time
import threading
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger
import json
import weakref
import gc

class MemoryCache:
    """Thread-safe in-memory cache with TTL support"""
    
    def __init__(self, max_size: int = 10000, cleanup_interval: int = 300):
        self._cache: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        
        logger.info(f"Initialized MemoryCache with max_size={max_size}")
        
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        
        # Only cleanup if interval has passed
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
            
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if entry['expires_at'] and entry['expires_at'] < current_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                
            # Force garbage collection if cache is getting large
            if len(self._cache) > self._max_size * 0.8:
                gc.collect()
                
            self._last_cleanup = current_time
    
    def _enforce_size_limit(self):
        """Remove oldest entries if cache exceeds max size"""
        with self._lock:
            if len(self._cache) <= self._max_size:
                return
                
            # Sort by access time and remove oldest
            items = sorted(
                self._cache.items(), 
                key=lambda x: x[1]['last_accessed']
            )
            
            # Remove oldest 20% when limit exceeded
            to_remove = len(items) - int(self._max_size * 0.8)
            
            for i in range(to_remove):
                key = items[i][0]
                del self._cache[key]
                
            logger.debug(f"Removed {to_remove} oldest cache entries to enforce size limit")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            self._cleanup_expired()
            
            with self._lock:
                entry = self._cache.get(key)
                if not entry:
                    return None
                
                # Check if expired
                if entry['expires_at'] and entry['expires_at'] < time.time():
                    del self._cache[key]
                    return None
                
                # Update access time
                entry['last_accessed'] = time.time()
                return entry['value']
                
        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache with expiration"""
        try:
            current_time = time.time()
            expires_at = current_time + expire if expire > 0 else None
            
            with self._lock:
                self._cache[key] = {
                    'value': value,
                    'expires_at': expires_at,
                    'created_at': current_time,
                    'last_accessed': current_time
                }
                
            self._enforce_size_limit()
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            with self._lock:
                if key in self._cache:
                    del self._cache[key]
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        return self.get(key) is not None
    
    def get_json(self, key: str) -> Optional[Dict]:
        """Get JSON value from cache"""
        try:
            value = self.get(key)
            if isinstance(value, str):
                return json.loads(value)
            elif isinstance(value, dict):
                return value
            return None
            
        except Exception as e:
            logger.error(f"Error getting JSON from cache: {e}")
            return None
    
    def set_json(self, key: str, value: Dict, expire: int = 3600) -> bool:
        """Set JSON value in cache"""
        try:
            # Store as dict directly (no need to serialize in memory)
            return self.set(key, value, expire)
            
        except Exception as e:
            logger.error(f"Error setting JSON cache: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern (simple wildcard support)"""
        try:
            with self._lock:
                # Simple pattern matching - just prefix/suffix wildcards
                if pattern.endswith('*'):
                    prefix = pattern[:-1]
                    keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
                elif pattern.startswith('*'):
                    suffix = pattern[1:]
                    keys_to_delete = [k for k in self._cache.keys() if k.endswith(suffix)]
                else:
                    # Exact match
                    keys_to_delete = [pattern] if pattern in self._cache else []
                
                for key in keys_to_delete:
                    del self._cache[key]
                
                return len(keys_to_delete)
                
        except Exception as e:
            logger.error(f"Error clearing pattern {pattern}: {e}")
            return 0
    
    def clear_user_data(self, user_id: int) -> int:
        """Clear all data for a specific user"""
        return self.clear_pattern(f"*user:{user_id}*")
    
    def get_cache_info(self) -> Dict:
        """Get cache statistics"""
        try:
            with self._lock:
                total_keys = len(self._cache)
                expired_count = 0
                current_time = time.time()
                
                for entry in self._cache.values():
                    if entry['expires_at'] and entry['expires_at'] < current_time:
                        expired_count += 1
                
                return {
                    'total_keys': total_keys,
                    'expired_keys': expired_count,
                    'active_keys': total_keys - expired_count,
                    'max_size': self._max_size,
                    'connected': True,
                    'type': 'memory'
                }
                
        except Exception as e:
            logger.error(f"Error getting cache info: {e}")
            return {'connected': False, 'error': str(e), 'type': 'memory'}
    
    def health_check(self) -> bool:
        """Check if cache is working"""
        try:
            test_key = f"health_check_{time.time()}"
            self.set(test_key, "test", 1)
            result = self.get(test_key) == "test"
            self.delete(test_key)
            return result
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False
    
    def clear_all(self) -> bool:
        """Clear all cache entries"""
        try:
            with self._lock:
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Cleared all {count} cache entries")
                return True
                
        except Exception as e:
            logger.error(f"Error clearing all cache: {e}")
            return False

# Global cache instance
cache = MemoryCache(max_size=10000, cleanup_interval=300)