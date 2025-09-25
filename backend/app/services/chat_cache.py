from ...redis_cache import cache
from typing import Optional, Dict
from loguru import logger
import hashlib
import json

class ChatCache:
    """Cache for chat responses to avoid repeated expensive LLM calls"""
    
    @staticmethod
    def _generate_cache_key(user_id: int, query: str, has_pdf: bool) -> str:
        """Generate a unique cache key for the query"""
        # Create a hash of the query for consistent key generation
        query_hash = hashlib.md5(query.encode()).hexdigest()
        prefix = "chat_pdf" if has_pdf else "chat_general"
        return f"{prefix}:user:{user_id}:query:{query_hash}"
    
    @staticmethod
    def get_cached_response(user_id: int, query: str, has_pdf: bool) -> Optional[Dict]:
        """Get cached response for a query"""
        try:
            cache_key = ChatCache._generate_cache_key(user_id, query, has_pdf)
            cached = cache.get_json(cache_key)
            
            if cached:
                logger.info(f"💾 Cache hit for user {user_id} query")
                return cached
            
            return None
        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
            return None
    
    @staticmethod
    def cache_response(user_id: int, query: str, has_pdf: bool, response: str, source: str, sources: list = None) -> bool:
        """Cache a response for a query with optional source citations"""
        try:
            cache_key = ChatCache._generate_cache_key(user_id, query, has_pdf)
            
            # Cache for 30 minutes for general queries, 1 hour for PDF queries
            expire_time = 3600 if has_pdf else 1800
            
            cached_data = {
                "response": response,
                "source": source,
                "query": query,
                "has_pdf": has_pdf
            }
            
            # Add sources if provided
            if sources:
                cached_data["sources"] = sources
            
            success = cache.set_json(cache_key, cached_data, expire=expire_time)
            
            if success:
                logger.info(f"💾 Cached response for user {user_id} with {len(sources) if sources else 0} sources")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
            return False
    
    @staticmethod
    def clear_user_chat_cache(user_id: int):
        """Clear all chat cache for a user"""
        try:
            # Clear both general and PDF chat caches
            general_pattern = f"chat_general:user:{user_id}:*"
            pdf_pattern = f"chat_pdf:user:{user_id}:*"
            
            cleared_general = cache.clear_pattern(general_pattern)
            cleared_pdf = cache.clear_pattern(pdf_pattern)
            
            logger.info(f"Cleared chat cache for user {user_id}: {cleared_general + cleared_pdf} entries")
            return cleared_general + cleared_pdf
            
        except Exception as e:
            logger.error(f"Error clearing user chat cache: {e}")
            return 0
