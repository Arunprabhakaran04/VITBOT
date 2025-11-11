import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from fastapi import FastAPI
from backend.app.routers import users, chat_rbac as chat, pdf_celery as pdf, admin, transcription
from backend.database_connection import get_connection_pool, close_connection_pool
from backend.app.services.background_task_service import background_service
from backend.app.services.pdf_processing_service import pdf_processing_service
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

# Configure production-ready logging (Windows-compatible)
import sys

# Set up console handler with UTF-8 encoding for Windows
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Set up file handler with UTF-8 encoding
file_handler = logging.FileHandler("vitbot.log", encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
)
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)

# Add loguru compatibility with standard logging (UTF-8 safe)
# Use enqueue=True to prevent file locking issues on Windows in multi-process environments
logger.add(
    "vitbot_detailed.log", 
    rotation="1 day", 
    retention="7 days", 
    level="DEBUG", 
    encoding='utf-8',
    enqueue=True  # Use queue to prevent file locking issues
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Production-ready application lifecycle management"""
    
    # STARTUP
    logger.info("VITBOT Backend starting up...")
    
    try:
        # Create required directories
        required_dirs = [
            "temp_uploads",
            "vector_stores", 
            "uploads/admin_documents",
            "vector_stores/admin_documents",
            "logs"
        ]
        
        for dir_path in required_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.info("Required directories created/verified")
        
        # Initialize database connection pool
        get_connection_pool()
        logger.info("Database connection pool initialized")
        
        # Initialize embeddings models at startup (production-ready approach)
        logger.info("Initializing embeddings models - this may take a few minutes on first run...")
        logger.info("Loading English model: BAAI/bge-small-en-v1.5 (384D)...")
        logger.info("Loading Multilingual model: intfloat/multilingual-e5-large (1024D)...")
        
        try:
            from backend.app.services.dual_embedding_manager import EmbeddingManager
            
            # Preload both models for optimal performance
            EmbeddingManager.preload_models(['english', 'multilingual'])
            
            logger.success("✓ English embeddings model loaded successfully (384D)")
            logger.success("✓ Multilingual embeddings model loaded successfully (1024D)")
            logger.success("Both embedding models are ready for multilingual RAG!")
            
        except Exception as e:
            logger.error(f"Failed to initialize embeddings models: {e}")
            logger.warning("PDF processing may be slower on first use")
            # Don't fail startup - embeddings will initialize on first use
        
        # Register PDF processing handlers  
        background_service.register_handler("process_pdf", pdf_processing_service.process_pdf_task)
        background_service.register_handler("process_admin_pdf", pdf_processing_service.process_admin_pdf_task)
        logger.info("PDF processing handlers registered")
        
        # Start background workers for PDF processing
        background_service.start()
        logger.info(f"Starting {background_service.max_workers} background workers for PDF processing...")
        logger.success("Background processing service started successfully")
        
        logger.success("VITBOT is ready! Access at http://localhost:8000")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # SHUTDOWN
    logger.info("VITBOT Backend shutting down...")
    try:
        background_service.stop()
        logger.info("Background workers stopped")
        close_connection_pool()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("Application shutdown complete")

# Create FastAPI app with integrated background processing
app = FastAPI(
    title="VITBOT API",
    description="Role-based PDF Chat System with Background Processing", 
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware - production ready
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(users.router)
app.include_router(chat.router) 
app.include_router(pdf.router)
app.include_router(admin.router)
app.include_router(transcription.router)

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/production deployment"""
    return {
        "status": "healthy",
        "service": "VITBOT Backend",
        "version": "2.0.0",
        "background_workers": {
            "running": background_service.running,
            "worker_count": background_service.max_workers,
            "queue_size": background_service.get_queue_size()
        },
        "database": "connected" if get_connection_pool() else "disconnected"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "VITBOT API is running", 
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "Role-based authentication",
            "Background PDF processing", 
            "Admin document management",
            "Real-time chat with RAG",
            "Zero external dependencies"
        ]
    }

# Production server startup (for Docker/standalone deployment)
if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WORKERS", "1"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting VITBOT Backend on {host}:{port}")
    logger.info(f"Workers: {workers}, Reload: {reload}")
    
    if workers > 1:
        # Multi-worker production mode 
        logger.info("Starting in multi-worker production mode")
        uvicorn.run(
            "backend.main:app",
            host=host,
            port=port,
            workers=workers,
            log_level="info"
        )
    else:
        # Single worker mode (development/small deployments)
        logger.info("Starting in single-worker mode")
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
