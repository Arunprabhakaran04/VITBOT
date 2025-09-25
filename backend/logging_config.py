"""
Centralized logging configuration using loguru
"""

import os
import sys
from loguru import logger

def setup_application_logging():
    """Configure loguru for the main application"""
    # Remove default handlers
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <blue>APP</blue> | <level>{message}</level>",
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # File handler
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    logger.add(
        os.path.join(log_dir, "app_{time:YYYY-MM-DD}.log"),
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | APP | {message}",
        level="DEBUG",
        backtrace=True,
        diagnose=True
    )

def setup_celery_logging():
    """Configure loguru for Celery (used in celery_app.py)"""
    # Remove default handlers
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>CELERY</cyan> | <level>{message}</level>",
        level=os.getenv("CELERY_LOG_LEVEL", "INFO").upper(),
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # File handler
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    logger.add(
        os.path.join(log_dir, "celery_{time:YYYY-MM-DD}.log"),
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | CELERY | {message}",
        level="DEBUG",
        backtrace=True,
        diagnose=True
    )

def setup_startup_logging():
    """Configure loguru for startup scripts"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <blue>STARTUP</blue> | <level>{message}</level>",
        level="INFO",
        colorize=True
    )

# Log levels configuration
LOG_LEVELS = {
    "DEBUG": "🐛",
    "INFO": "ℹ️",
    "SUCCESS": "✅",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🚨"
}

# Custom log messages with emojis
def log_startup(message: str):
    """Log startup messages with rocket emoji"""
    logger.info(f"🚀 {message}")

def log_pdf_processing(message: str):
    """Log PDF processing messages"""
    logger.info(f"📄 {message}")

def log_cache_operation(message: str):
    """Log cache operations"""
    logger.info(f"🗂️ {message}")

def log_database_operation(message: str):
    """Log database operations"""
    logger.info(f"🗃️ {message}")

def log_user_action(message: str):
    """Log user actions"""
    logger.info(f"👤 {message}")

def log_error(message: str):
    """Log errors with error emoji"""
    logger.error(f"❌ {message}")

def log_success(message: str):
    """Log success messages"""
    logger.success(f"✅ {message}")

def log_warning(message: str):
    """Log warnings"""
    logger.warning(f"⚠️ {message}") 