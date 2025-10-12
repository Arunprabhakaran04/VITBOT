#!/usr/bin/env python3
"""
Comprehensive Cleanup Script for VITBOT
=======================================

This script completely cleans all document-related data including:
1. Database records (admin_documents, document_chunks, user_tasks)
2. Vector stores (FAISS indexes and metadata)
3. File uploads (admin documents and user uploads)
4. Background task results

Usage: python comprehensive_cleanup.py
"""

import os
import shutil
import sys
import psycopg2
from pathlib import Path
import logging
import subprocess

def activate_virtual_environment():
    """Activate virtual environment if it exists"""
    venv_paths = [
        "venv\\Scripts\\activate.bat",  # Windows
        "venv/bin/activate",           # Linux/Mac
        ".venv\\Scripts\\activate.bat", # Windows alternative
        ".venv/bin/activate"           # Linux/Mac alternative
    ]
    
    for venv_path in venv_paths:
        if os.path.exists(venv_path):
            print(f"[VENV] Found virtual environment: {venv_path}")
            
            # For Windows batch files, we need to modify the current process
            if venv_path.endswith('.bat'):
                venv_dir = os.path.dirname(os.path.dirname(venv_path))
                scripts_dir = os.path.join(venv_dir, 'Scripts')
                
                # Add venv to PATH
                current_path = os.environ.get('PATH', '')
                if scripts_dir not in current_path:
                    os.environ['PATH'] = scripts_dir + os.pathsep + current_path
                    print(f"[VENV] Added to PATH: {scripts_dir}")
                
                # Set virtual environment variable
                os.environ['VIRTUAL_ENV'] = venv_dir
                print(f"[VENV] Set VIRTUAL_ENV: {venv_dir}")
                return True
            
    print("[VENV] No virtual environment found, continuing with system Python")
    return False

# Activate virtual environment first
activate_virtual_environment()

# Add backend to path for imports
backend_path = Path(__file__).parent / "backend"
sys.path.append(str(backend_path))

from backend.database_connection import get_db_connection

# Setup logging with UTF-8 encoding
import sys

# Setup console handler with UTF-8 encoding for Windows
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))

# Setup file handler
file_handler = logging.FileHandler('cleanup.log', encoding='utf-8')
file_handler.setLevel(logging.INFO) 
file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

def cleanup_database():
    """Clean all document-related database tables"""
    logger.info("[DB] Starting database cleanup...")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get counts before cleanup
            cursor.execute("SELECT COUNT(*) FROM admin_documents")
            result = cursor.fetchone()
            admin_docs_count = result['count'] if result else 0
            
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            result = cursor.fetchone()
            chunks_count = result['count'] if result else 0
            
            cursor.execute("SELECT COUNT(*) FROM user_tasks WHERE task_type IN ('pdf_processing', 'admin_pdf_processing')")
            result = cursor.fetchone()
            tasks_count = result['count'] if result else 0
            
            logger.info(f"Found {admin_docs_count} admin documents, {chunks_count} chunks, {tasks_count} tasks")
            
            # Delete in reverse dependency order
            logger.info("Deleting document chunks...")
            cursor.execute("DELETE FROM document_chunks")
            deleted_chunks = cursor.rowcount
            
            logger.info("Deleting admin documents...")
            cursor.execute("DELETE FROM admin_documents")
            deleted_docs = cursor.rowcount
            
            logger.info("Deleting PDF processing tasks...")
            cursor.execute("DELETE FROM user_tasks WHERE task_type IN ('pdf_processing', 'admin_pdf_processing')")
            deleted_tasks = cursor.rowcount
            
            # Reset sequences (only if tables exist)
            try:
                logger.info("Resetting ID sequences...")
                cursor.execute("ALTER SEQUENCE IF EXISTS admin_documents_id_seq RESTART WITH 1")
                cursor.execute("ALTER SEQUENCE IF EXISTS document_chunks_id_seq RESTART WITH 1") 
                cursor.execute("ALTER SEQUENCE IF EXISTS user_tasks_id_seq RESTART WITH 1")
            except Exception as seq_error:
                logger.warning(f"Sequence reset warning (non-critical): {seq_error}")
            
            conn.commit()
            logger.info(f"[SUCCESS] Database cleanup completed: {deleted_docs} docs, {deleted_chunks} chunks, {deleted_tasks} tasks deleted")
            
    except Exception as e:
        logger.error(f"[ERROR] Database cleanup failed: {e}")
        raise

def cleanup_vector_stores():
    """Clean all vector store files and directories"""
    logger.info("[VECTOR] Starting vector store cleanup...")
    
    vector_stores_paths = [
        "vector_stores",
        "backend/vector_stores", 
        "uploads/admin_documents/*/vector_store",  # Individual document stores
    ]
    
    total_removed = 0
    
    for path_pattern in vector_stores_paths:
        if "*" in path_pattern:
            # Handle wildcard patterns
            from glob import glob
            matching_paths = glob(path_pattern)
            for path in matching_paths:
                if os.path.exists(path):
                    try:
                        shutil.rmtree(path)
                        logger.info(f"Removed vector store: {path}")
                        total_removed += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove {path}: {e}")
        else:
            # Handle direct paths
            if os.path.exists(path_pattern):
                try:
                    shutil.rmtree(path_pattern)
                    logger.info(f"Removed vector store directory: {path_pattern}")
                    total_removed += 1
                except Exception as e:
                    logger.warning(f"Failed to remove {path_pattern}: {e}")
    
    logger.info(f"[SUCCESS] Vector store cleanup completed. Removed {total_removed} directories")

def cleanup_uploads():
    """Clean all uploaded files"""
    logger.info("[FILES] Starting file upload cleanup...")
    
    upload_paths = [
        "uploads/admin_documents",
        "backend/uploads/admin_documents",
        "temp_uploads",
        "backend/temp_uploads"
    ]
    
    total_files = 0
    total_dirs = 0
    
    for upload_path in upload_paths:
        if os.path.exists(upload_path):
            try:
                # Count files and directories first
                for root, dirs, files in os.walk(upload_path):
                    total_files += len(files)
                    total_dirs += len(dirs)
                
                # Remove the entire directory tree
                shutil.rmtree(upload_path)
                logger.info(f"Removed upload directory: {upload_path}")
                
                # Recreate empty directory
                os.makedirs(upload_path, exist_ok=True)
                logger.info(f"Recreated empty directory: {upload_path}")
                
            except Exception as e:
                logger.warning(f"Failed to clean {upload_path}: {e}")
    
    logger.info(f"[SUCCESS] Upload cleanup completed. Removed {total_files} files and {total_dirs} directories")

def cleanup_logs():
    """Clean application logs (optional)"""
    logger.info("[LOGS] Starting log cleanup...")
    
    log_paths = [
        "logs",
        "backend/logs",
        "*.log"
    ]
    
    total_removed = 0
    
    for log_path in log_paths:
        if "*" in log_path:
            from glob import glob
            matching_files = glob(log_path)
            for file_path in matching_files:
                if os.path.isfile(file_path) and file_path != 'cleanup.log':  # Don't delete current log
                    try:
                        os.remove(file_path)
                        logger.info(f"Removed log file: {file_path}")
                        total_removed += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove {file_path}: {e}")
        else:
            if os.path.exists(log_path) and os.path.isdir(log_path):
                try:
                    shutil.rmtree(log_path)
                    logger.info(f"Removed log directory: {log_path}")
                    total_removed += 1
                    
                    # Recreate empty directory
                    os.makedirs(log_path, exist_ok=True)
                    logger.info(f"Recreated empty log directory: {log_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean {log_path}: {e}")
    
    logger.info(f"[SUCCESS] Log cleanup completed. Removed {total_removed} items")

def cleanup_json_outputs():
    """Clean JSON debug output files"""
    logger.info("[JSON] Starting JSON output cleanup...")
    
    json_patterns = [
        "uploads/**/*_chunks.json",
        "backend/uploads/**/*_chunks.json",
        "**/*_processing_debug.json"
    ]
    
    total_removed = 0
    
    from glob import glob
    for pattern in json_patterns:
        matching_files = glob(pattern, recursive=True)
        for file_path in matching_files:
            try:
                os.remove(file_path)
                logger.info(f"Removed JSON output: {file_path}")
                total_removed += 1
            except Exception as e:
                logger.warning(f"Failed to remove {file_path}: {e}")
    
    logger.info(f"[SUCCESS] JSON output cleanup completed. Removed {total_removed} files")

def verify_cleanup():
    """Verify that cleanup was successful"""
    logger.info("[VERIFY] Verifying cleanup...")
    
    # Check database
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM admin_documents")
            result = cursor.fetchone()
            admin_docs = result['count'] if result else 0
            
            cursor.execute("SELECT COUNT(*) FROM document_chunks") 
            result = cursor.fetchone()
            chunks = result['count'] if result else 0
            
            if admin_docs == 0 and chunks == 0:
                logger.info("[SUCCESS] Database verification passed - all records cleaned")
            else:
                logger.warning(f"[WARNING] Database verification failed - {admin_docs} docs, {chunks} chunks remaining")
                
    except Exception as e:
        logger.error(f"[ERROR] Database verification failed: {e}")
    
    # Check vector stores
    vector_exists = any([
        os.path.exists("vector_stores"),
        os.path.exists("backend/vector_stores")
    ])
    
    if not vector_exists:
        logger.info("[SUCCESS] Vector store verification passed - directories removed")
    else:
        logger.warning("[WARNING] Vector store verification failed - some directories still exist")
    
    logger.info("[VERIFY] Cleanup verification completed")

def main():
    """Main cleanup function"""
    print("VITBOT Comprehensive Cleanup Tool")
    print("=" * 50)
    
    response = input("This will DELETE ALL documents, chunks, vector stores and uploads. Continue? (yes/no): ")
    
    if response.lower() != 'yes':
        print("[CANCELLED] Cleanup cancelled by user")
        return
    
    try:
        logger.info("[START] Starting comprehensive cleanup...")
        
        # Run cleanup operations
        cleanup_database()
        cleanup_vector_stores()  
        cleanup_uploads()
        cleanup_json_outputs()
        # cleanup_logs()  # Uncomment if you want to clean logs too
        
        # Verify cleanup
        verify_cleanup()
        
        logger.info("[COMPLETE] Comprehensive cleanup completed successfully!")
        print("\n[SUCCESS] All cleanup operations completed!")
        print("[LOG] Check 'cleanup.log' for detailed results")
        
    except Exception as e:
        logger.error(f"[FAILED] Cleanup failed: {e}")
        print(f"\n[ERROR] Cleanup failed: {e}")
        print("[LOG] Check 'cleanup.log' for error details")
        sys.exit(1)

if __name__ == "__main__":
    main()