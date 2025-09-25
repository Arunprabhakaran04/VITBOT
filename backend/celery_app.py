from celery import Celery
from celery.signals import setup_logging
import os
import sys
from loguru import logger

# Configure loguru for Celery
def setup_celery_logging(**kwargs):
    """Configure loguru for Celery logging"""
    # Remove default handlers
    logger.remove()
    
    # Add colored console handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>CELERY</cyan> | <level>{message}</level>",
        level=os.getenv("CELERY_LOG_LEVEL", "INFO").upper(),
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Add file handler for persistent logging
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

# Set up logging when Celery starts
setup_logging.connect(setup_celery_logging)

# Configure Celery
celery_app = Celery(
    "pdf_processor",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=["backend.tasks"]
)

# Configure Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600, 
    broker_connection_retry_on_startup=True,  
    worker_max_tasks_per_child=1,
    task_routes={
        "backend.tasks.process_pdf_task": {"queue": "pdf_processing"},
    },
    # Disable Celery's default logging
    worker_log_format="",
    worker_task_log_format="",
    worker_hijack_root_logger=False,
    worker_log_color=False,
)

if __name__ == "__main__":
    celery_app.start() 