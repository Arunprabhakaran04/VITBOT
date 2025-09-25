from ...database_connection import get_db_connection
from typing import List, Dict, Optional
from datetime import datetime, timezone

class ChatDBService:
    
    @staticmethod
    def create_or_get_chat(user_id: int, chat_id: str, first_message: str = None) -> Dict:
        """Create a new chat or get existing chat"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if chat already exists
            cursor.execute(
                "SELECT chat_id, title, created_at, updated_at, message_count FROM chats WHERE chat_id = %s",
                (chat_id,)
            )
            existing_chat = cursor.fetchone()
            
            if existing_chat:
                return dict(existing_chat)
            
            # Create new chat
            # Generate title from first message (first 50 chars or default)
            title = first_message[:50] + "..." if first_message and len(first_message) > 50 else first_message or "New Chat"
            
            now = datetime.now(timezone.utc)
            cursor.execute("""
                INSERT INTO chats (chat_id, user_id, title, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING chat_id, title, created_at, updated_at, message_count
            """, (chat_id, user_id, title, now, now))
            
            new_chat = cursor.fetchone()
            conn.commit()
            return dict(new_chat)
    
    @staticmethod
    def save_message(chat_id: str, role: str, content: str, source: str = "general") -> bool:
        """Save a message to the database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Insert message
            now = datetime.now(timezone.utc)
            cursor.execute("""
                INSERT INTO messages (chat_id, role, content, source, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (chat_id, role, content, source, now))
            
            # Update chat's updated_at and message_count
            cursor.execute("""
                UPDATE chats 
                SET updated_at = %s, 
                    message_count = (SELECT COUNT(*) FROM messages WHERE chat_id = %s)
                WHERE chat_id = %s
            """, (now, chat_id, chat_id))
            
            conn.commit()
            return True
    
    @staticmethod
    def get_user_chats(user_id: int) -> List[Dict]:
        """Get all chats for a user, ordered by most recent"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT chat_id, title, created_at, updated_at, message_count
                FROM chats 
                WHERE user_id = %s 
                ORDER BY updated_at DESC
            """, (user_id,))
            
            chats = cursor.fetchall()
            return [dict(chat) for chat in chats]
    
    @staticmethod
    def get_chat_messages(chat_id: str, user_id: int) -> List[Dict]:
        """Get all messages for a specific chat (with user verification)"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verify chat belongs to user
            cursor.execute("""
                SELECT 1 FROM chats WHERE chat_id = %s AND user_id = %s
            """, (chat_id, user_id))
            
            if not cursor.fetchone():
                raise Exception("Chat not found or access denied")
            
            # Get messages
            cursor.execute("""
                SELECT role, content, source, created_at
                FROM messages 
                WHERE chat_id = %s 
                ORDER BY created_at ASC
            """, (chat_id,))
            
            messages = cursor.fetchall()
            return [dict(message) for message in messages]
    
    @staticmethod
    def delete_chat(chat_id: str, user_id: int) -> bool:
        """Delete a chat and all its messages (with user verification)"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verify ownership and delete
            cursor.execute("""
                DELETE FROM chats 
                WHERE chat_id = %s AND user_id = %s
            """, (chat_id, user_id))
            
            if cursor.rowcount == 0:
                raise Exception("Chat not found or access denied")
            
            conn.commit()
            return True
    
    @staticmethod
    def update_chat_title(chat_id: str, user_id: int, new_title: str) -> bool:
        """Update chat title"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc)
            cursor.execute("""
                UPDATE chats 
                SET title = %s, updated_at = %s
                WHERE chat_id = %s AND user_id = %s
            """, (new_title, now, chat_id, user_id))
            
            if cursor.rowcount == 0:
                raise Exception("Chat not found or access denied")
            
            conn.commit()
            return True