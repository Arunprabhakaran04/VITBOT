import psycopg2
from typing import Optional

def save_vector_store_path(conn, user_id: int, vector_store_path: str, language: str = 'english', embedding_model: str = None):
    """Save vector store path with language and embedding model information"""
    cursor = conn.cursor()
    try:
        # Set default embedding model for English if not provided
        if embedding_model is None:
            embedding_model = 'BAAI/bge-small-en-v1.5'
        
        # Deactivate previous vector stores for this user
        cursor.execute("UPDATE user_vector_stores SET is_active = FALSE WHERE user_id = %s", (user_id,))
        
        # Insert new vector store with language information
        cursor.execute("""
            INSERT INTO user_vector_stores (user_id, vector_store_path, language, embedding_model, is_active) 
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, vector_store_path, language, embedding_model, True))
        
        conn.commit()
        print(f"Saved {language} vector store for user {user_id}: {vector_store_path}")
        print(f"Using embedding model: {embedding_model}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error saving vector store path: {e}")
        raise e
    finally:
        cursor.close()

def get_user_vector_store_path(conn, user_id: int) -> Optional[str]:
    """Get vector store path (legacy function for backward compatibility)"""
    info = get_user_vector_store_info(conn, user_id)
    return info['path'] if info else None

def get_user_vector_store_info(conn, user_id: int) -> Optional[dict]:
    """Get vector store path, language, and embedding model information"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT vector_store_path, language, embedding_model, created_at
            FROM user_vector_stores 
            WHERE user_id = %s AND is_active = TRUE 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (user_id,))
        
        row = cursor.fetchone()
        if row:
            # Handle both tuple and RealDictRow formats
            if isinstance(row, dict):
                info = {
                    'path': row['vector_store_path'],
                    'language': row['language'] or 'english',  # Default to english for legacy records
                    'embedding_model': row['embedding_model'] or 'BAAI/bge-small-en-v1.5',  # Default for legacy
                    'created_at': row['created_at']
                }
            else:
                info = {
                    'path': row[0],
                    'language': row[1] or 'english',  # Default to english for legacy records
                    'embedding_model': row[2] or 'BAAI/bge-small-en-v1.5',  # Default for legacy
                    'created_at': row[3]
                }
            print(f"Found {info['language']} vector store for user {user_id}: {info['path']}")
            return info
        else:
            print(f"No active vector store found for user {user_id}")
            return None
            
    except Exception as e:
        print(f"Error getting vector store info: {e}")
        return None
    finally:
        cursor.close()

def get_user_language_stats(conn, user_id: int) -> dict:
    """Get statistics about user's document languages"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT language, COUNT(*) as count, MAX(created_at) as latest
            FROM user_vector_stores 
            WHERE user_id = %s 
            GROUP BY language
            ORDER BY count DESC
        """, (user_id,))
        
        rows = cursor.fetchall()
        stats = {
            'total_documents': sum(row[1] for row in rows),
            'languages': {}
        }
        
        for row in rows:
            stats['languages'][row[0]] = {
                'count': row[1],
                'latest': row[2]
            }
        
        return stats
        
    except Exception as e:
        print(f"Error getting language stats: {e}")
        return {'total_documents': 0, 'languages': {}}
    finally:
        cursor.close()