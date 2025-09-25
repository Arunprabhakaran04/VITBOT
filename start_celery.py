#!/usr/bin/env python3
"""
Script to start Celery worker for PDF processing
Usage: python start_celery.py
"""

import os
import sys
from loguru import logger
from backend.celery_app import celery_app

def setup_startup_logging():
    """Configure loguru for startup logging"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <blue>STARTUP</blue> | <level>{message}</level>",
        level="INFO",
        colorize=True
    )

if __name__ == "__main__":
    setup_startup_logging()
    
    # Get configuration
    log_level = os.getenv("CELERY_LOG_LEVEL", "info").lower()
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    logger.info("🚀 Starting Celery Worker for PDF Processing")
    logger.info(f"📊 Log Level: {log_level.upper()}")
    logger.info(f"🔗 Redis URL: {redis_url}")
    logger.info("🔧 Worker Configuration:")
    logger.info("   • Pool: solo (Windows compatible)")
    logger.info("   • Queue: pdf_processing")
    logger.info("   • Gossip: disabled")
    logger.info("   • Mingle: disabled")
    logger.info("   • Heartbeat: disabled")
    logger.info("🎯 Worker starting...")
    
    try:
        # Start the worker with pool=solo for Windows compatibility
        celery_app.worker_main([
            "worker",
            "--loglevel=" + log_level,
            "--pool=solo",  # Use solo pool for Windows
            "--queues=pdf_processing",
            "--without-gossip",  # Disable gossip for better Windows compatibility
            "--without-mingle",  # Disable mingle for better Windows compatibility
            "--without-heartbeat"  # Disable heartbeat for better Windows compatibility
        ])
    except KeyboardInterrupt:
        logger.warning("🛑 Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"❌ Failed to start Celery worker: {str(e)}")
        sys.exit(1) 