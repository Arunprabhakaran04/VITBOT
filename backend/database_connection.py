from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv
import os
from contextlib import contextmanager

load_dotenv()

database = os.getenv("database", "fastapi")
user = os.getenv("user")
password = os.getenv("password_db")

# Create a connection pool
_pool = None

def get_connection_pool():
    global _pool
    if _pool is None:
        try:
            _pool = SimpleConnectionPool(
                minconn=1,
                maxconn=20,  # Adjust based on your needs
                host="localhost",
                database=database,
                user=user,
                password=password,
                cursor_factory=RealDictCursor
            )
            print("Connection pool created successfully")
        except Exception as e:
            print(f"Failed to create connection pool: {e}")
            return None
    return _pool

@contextmanager
def get_db_connection():
    """Context manager for database connections from the pool"""
    pool = get_connection_pool()
    if pool is None:
        raise Exception("Database connection pool not available")
    
    conn = None
    try:
        conn = pool.getconn()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            pool.putconn(conn)

def close_connection_pool():
    """Close the connection pool (call this on application shutdown)"""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        print("Connection pool closed")

# Legacy function for backward compatibility (deprecated)
def get_db_connection_legacy():
    """Legacy function - use get_db_connection() context manager instead"""
    try:
        conn = connect(
            host="localhost", 
            database=database, 
            user=user, 
            password=password, 
            cursor_factory=RealDictCursor
        )
        print("successfully connected to database")
        return conn
    except Exception as e:
        print("couldn't connect to the database")
        print(f"error is {e}")
        return None
    