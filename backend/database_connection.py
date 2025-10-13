"""Environment-driven PostgreSQL connection pool.

Supports three modes (chosen by env vars):
 - DATABASE_URL (full DSN) -> e.g. Neon
 - DB_HOST set to 'localhost' or IP -> local Postgres
 - DB_HOST set to service name like 'db' -> Docker compose Postgres

Env variables (preferred):
 - DATABASE_URL (optional) : full postgres URL
 - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD : used when DATABASE_URL is not set
 - DB_POOL_MIN, DB_POOL_MAX : pool sizes (defaults: 1, 10)

Usage:
 - Call get_connection_pool() to lazily initialize and return pool
 - Use get_db_connection() as a contextmanager to get a connection
 - Call close_connection_pool() on shutdown
"""
from contextlib import contextmanager
import os
import logging
from urllib.parse import urlparse, parse_qs

from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

logger = logging.getLogger(__name__)

# Read env
DATABASE_URL = os.getenv("DATABASE_URL")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", os.getenv("database", "VITBOT"))
DB_USER = os.getenv("DB_USER", os.getenv("user"))
DB_PASSWORD = os.getenv("DB_PASSWORD", os.getenv("password_db"))

# Pool sizing
try:
    DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "1"))
    DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))
except ValueError:
    DB_POOL_MIN = 1
    DB_POOL_MAX = 10

# Internal pool reference
_pool: SimpleConnectionPool | None = None


def _build_conn_params_from_url(dsn: str) -> dict:
    """Parse a DATABASE_URL into connection params for psycopg2.connect/simple pool.

    Supports query params included in the URL (sslmode, etc.) but returns only
    the common args accepted by psycopg2.connect.
    """
    parsed = urlparse(dsn)
    params = {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/"),
        "user": parsed.username,
        "password": parsed.password,
    }
    # include any query params as extras (sslmode etc.) as part of dsn when needed
    # psycopg2.connect will accept a full dsn string, so keep raw url too.
    return params


def _build_conn_params_from_env() -> dict:
    """Construct connection params from explicit env vars.

    If DATABASE_URL is set, prefer parsing it.
    """
    if DATABASE_URL:
        logger.debug("Using DATABASE_URL for DB connection")
        return _build_conn_params_from_url(DATABASE_URL)

    # Fallback to DB_HOST-based config
    if not DB_HOST:
        raise RuntimeError("No DATABASE_URL or DB_HOST found in environment")

    return {
        "host": DB_HOST,
        "port": int(DB_PORT),
        "database": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
    }


def get_connection_pool():
    """Lazily initialize and return a SimpleConnectionPool.

    This function is idempotent and will return the existing pool if already created.
    """
    global _pool
    if _pool is not None:
        return _pool

    params = _build_conn_params_from_env()

    try:
        if DATABASE_URL:
            # If we have full DATABASE_URL, pass it directly to connect via dsn
            # The pool accepts the same kwargs as psycopg2.connect, so include dsn
            _pool = SimpleConnectionPool(
                minconn=DB_POOL_MIN,
                maxconn=DB_POOL_MAX,
                dsn=DATABASE_URL,
                cursor_factory=RealDictCursor,
            )
        else:
            _pool = SimpleConnectionPool(
                minconn=DB_POOL_MIN,
                maxconn=DB_POOL_MAX,
                host=params["host"],
                port=params["port"],
                database=params["database"],
                user=params.get("user"),
                password=params.get("password"),
                cursor_factory=RealDictCursor,
            )

        logger.info("Database connection pool created (min=%s, max=%s)", DB_POOL_MIN, DB_POOL_MAX)
    except Exception as exc:
        logger.exception("Failed to create database connection pool: %s", exc)
        _pool = None
        raise

    return _pool


@contextmanager
def get_db_connection():
    """Context manager yielding a connection from the shared pool.

    Usage:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(...)
    """
    pool = get_connection_pool()
    conn = None
    try:
        conn = pool.getconn()
        yield conn
        # commit by default after successful use
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn is not None:
            pool.putconn(conn)


def is_db_connected() -> bool:
    """Quick health-check: attempt to get and release a connection."""
    try:
        pool = get_connection_pool()
        if not pool:
            return False
        conn = pool.getconn()
        pool.putconn(conn)
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False


def close_connection_pool():
    """Close the pool when application is shutting down."""
    global _pool
    if _pool:
        try:
            _pool.closeall()
            logger.info("Database connection pool closed")
        except Exception:
            logger.exception("Error closing database connection pool")
        finally:
            _pool = None


# Backward-compatible helper for raw single connection (not recommended)
def get_db_connection_legacy():
    params = _build_conn_params_from_env()
    try:
        if DATABASE_URL:
            # let psycopg2 parse the full DSN
            return connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return connect(
            host=params["host"],
            port=params["port"],
            database=params["database"],
            user=params.get("user"),
            password=params.get("password"),
            cursor_factory=RealDictCursor,
        )
    except Exception:
        logger.exception("Legacy DB connection failed")
        return None
