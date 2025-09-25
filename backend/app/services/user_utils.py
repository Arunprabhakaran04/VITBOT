from ...database_connection import get_db_connection
from typing import Optional, Dict

class UserUtils:
    
    @staticmethod
    def has_active_vector_store(user_id: int) -> bool:
        """Check if user has an active vector store"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM user_vector_store 
                    WHERE user_id = %s AND is_active = true
                    LIMIT 1
                """, (user_id,))
                
                result = cursor.fetchone()
                return result is not None
                
        except Exception as e:
            print(f"Error checking vector store: {str(e)}")
            return False
    
    @staticmethod
    def get_user_vector_store_info(user_id: int) -> Optional[Dict]:
        """Get active vector store info for user"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, vector_store_path, created_at, is_active
                    FROM user_vector_store 
                    WHERE user_id = %s AND is_active = true
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (user_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            print(f"Error fetching vector store info: {str(e)}")
            return None
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, email, password, created_at
                    FROM users 
                    WHERE email = %s
                """, (email,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            print(f"Error fetching user: {str(e)}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, email, created_at
                    FROM users 
                    WHERE id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            print(f"Error fetching user: {str(e)}")
            return None