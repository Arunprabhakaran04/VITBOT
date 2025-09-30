#!/usr/bin/env python3
"""
Complete Fresh Cleanup Script for VITBOT Admin Documents
This script removes ALL traces of uploaded documents to allow fresh uploads without hash conflicts
"""
import os
import shutil
import sys
from pathlib import Path
import json

# Add backend to path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from database_connection import get_db_connection
from loguru import logger

def clear_redis_cache():
    """Clear all Redis cache entries related to documents"""
    try:
        from redis_cache import cache
        
        # Patterns to clear
        patterns = [
            "vectorstore:user:*",
            "combined_vectorstore:user:*",
            "global_vectorstore",
            "admin_documents:*", 
            "document_chunks:*",
            "vector_store:*"
        ]
        
        total_cleared = 0
        for pattern in patterns:
            try:
                if pattern.endswith("*"):
                    cleared = cache.clear_pattern(pattern)
                else:
                    cleared = 1 if cache.delete(pattern) else 0
                total_cleared += cleared
                logger.info(f"Cleared {cleared} entries for pattern: {pattern}")
            except Exception as e:
                logger.warning(f"Could not clear pattern {pattern}: {e}")
        
        logger.success(f"Total Redis entries cleared: {total_cleared}")
        
    except Exception as e:
        logger.warning(f"Could not clear Redis cache: {e}")
        logger.info("Continuing with cleanup...")

def clear_database_completely():
    """Clear ALL document-related data from database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # List of tables to check and clear (in dependency order)
            tables_info = [
                ("document_chunks", "Document text chunks"),
                ("global_vector_store", "Global vector store records"),
                ("admin_documents", "Admin document metadata"),
            ]
            
            total_records_cleared = 0
            
            for table_name, description in tables_info:
                try:
                    # Check if table exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public'
                            AND table_name = %s
                        )
                    """, (table_name,))
                    
                    table_exists = cursor.fetchone()[0]
                    
                    if table_exists:
                        # Get current count
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
                        
                        if count > 0:
                            logger.info(f"Found {count} records in {table_name}")
                            
                            # Clear the table completely
                            cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")
                            total_records_cleared += count
                            logger.success(f"✓ Cleared {count} records from {table_name}")
                        else:
                            logger.info(f"Table {table_name} is already empty")
                    else:
                        logger.info(f"Table {table_name} does not exist")
                        
                except Exception as e:
                    logger.error(f"Error clearing {table_name}: {e}")
                    # Try alternative cleanup
                    try:
                        cursor.execute(f"DELETE FROM {table_name}")
                        logger.warning(f"Used DELETE instead of TRUNCATE for {table_name}")
                    except:
                        logger.error(f"Could not clear {table_name} at all")
            
            # Clear admin processing tasks
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM user_tasks 
                    WHERE task_type IN ('admin_pdf_processing', 'document_processing', 'vector_store_creation')
                """)
                task_count = cursor.fetchone()[0]
                
                if task_count > 0:
                    cursor.execute("""
                        DELETE FROM user_tasks 
                        WHERE task_type IN ('admin_pdf_processing', 'document_processing', 'vector_store_creation')
                    """)
                    total_records_cleared += task_count
                    logger.success(f"✓ Cleared {task_count} processing tasks")
                    
            except Exception as e:
                logger.warning(f"Could not clear processing tasks: {e}")
            
            # Reset sequences to start from 1
            sequences_to_reset = [
                "admin_documents_id_seq",
                "document_chunks_id_seq"
            ]
            
            for seq_name in sequences_to_reset:
                try:
                    cursor.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH 1")
                    logger.info(f"Reset sequence {seq_name}")
                except Exception as e:
                    logger.warning(f"Could not reset sequence {seq_name}: {e}")
            
            conn.commit()
            logger.success(f"🗄️  Database cleanup completed! Cleared {total_records_cleared} total records")
            
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")
        raise

def clear_file_storage():
    """Clear all uploaded files and vector stores"""
    try:
        base_dir = Path(__file__).parent / 'backend'
        
        # Directories to clear
        directories_to_clear = [
            (base_dir / 'uploads' / 'admin_documents', 'uploaded admin documents'),
            (base_dir / 'vector_stores' / 'admin_documents', 'admin vector stores'),
            (base_dir / 'vector_stores' / 'global', 'global vector stores'),  # if exists
        ]
        
        total_files_removed = 0
        total_dirs_removed = 0
        
        for dir_path, description in directories_to_clear:
            if dir_path.exists():
                if dir_path.is_dir():
                    # Count files first
                    files_count = sum(1 for f in dir_path.rglob('*') if f.is_file())
                    dirs_count = sum(1 for d in dir_path.rglob('*') if d.is_dir())
                    
                    if files_count > 0 or dirs_count > 0:
                        logger.info(f"Removing {files_count} files and {dirs_count} directories from {description}")
                        
                        # Remove all contents
                        shutil.rmtree(dir_path)
                        
                        # Recreate empty directory
                        dir_path.mkdir(parents=True, exist_ok=True)
                        
                        total_files_removed += files_count
                        total_dirs_removed += dirs_count
                        
                        logger.success(f"✓ Cleared {description}")
                    else:
                        logger.info(f"Directory {description} is already empty")
                else:
                    logger.info(f"Path {dir_path} is not a directory")
            else:
                logger.info(f"Directory {dir_path} does not exist")
        
        # Also clear any .faiss and .pkl files in the vector_stores root
        vector_stores_root = base_dir / 'vector_stores'
        if vector_stores_root.exists():
            for file_path in vector_stores_root.glob('*.faiss'):
                file_path.unlink()
                total_files_removed += 1
                logger.info(f"Removed FAISS file: {file_path.name}")
                
            for file_path in vector_stores_root.glob('*.pkl'):
                file_path.unlink() 
                total_files_removed += 1
                logger.info(f"Removed pickle file: {file_path.name}")
        
        logger.success(f"📁 File storage cleanup completed! Removed {total_files_removed} files and {total_dirs_removed} directories")
        
    except Exception as e:
        logger.error(f"Error during file storage cleanup: {e}")
        raise

def clear_celery_tasks():
    """Clear any pending/running document processing tasks"""
    try:
        # Try to clear Celery tasks related to document processing
        from celery_app import celery_app
        
        # Get active tasks
        active_tasks = celery_app.control.inspect().active()
        if active_tasks:
            task_count = sum(len(tasks) for tasks in active_tasks.values())
            if task_count > 0:
                logger.info(f"Found {task_count} active Celery tasks")
                
                # Revoke all active document processing tasks
                celery_app.control.purge()
                logger.success("✓ Purged all Celery tasks")
            else:
                logger.info("No active Celery tasks found")
        else:
            logger.info("No Celery workers detected")
            
    except Exception as e:
        logger.warning(f"Could not clear Celery tasks: {e}")
        logger.info("Continuing with cleanup...")

def verify_cleanup():
    """Verify that cleanup was successful"""
    logger.info("🔍 Verifying cleanup...")
    
    issues = []
    
    # Check database
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            tables_to_check = ["admin_documents", "document_chunks", "global_vector_store"]
            
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    if count > 0:
                        issues.append(f"Table {table} still has {count} records")
                    else:
                        logger.info(f"✓ Table {table} is empty")
                except Exception as e:
                    logger.warning(f"Could not check table {table}: {e}")
                    
    except Exception as e:
        issues.append(f"Could not verify database: {e}")
    
    # Check file system
    base_dir = Path(__file__).parent / 'backend'
    
    upload_dir = base_dir / 'uploads' / 'admin_documents'
    if upload_dir.exists():
        files = list(upload_dir.glob('*'))
        if files:
            issues.append(f"Upload directory still has {len(files)} files")
        else:
            logger.info("✓ Upload directory is empty")
    
    vector_dir = base_dir / 'vector_stores' / 'admin_documents'
    if vector_dir.exists():
        files = list(vector_dir.glob('*'))
        if files:
            issues.append(f"Vector stores directory still has {len(files)} files")
        else:
            logger.info("✓ Vector stores directory is empty")
    
    if issues:
        logger.warning("⚠️  Some issues found after cleanup:")
        for issue in issues:
            logger.warning(f"  - {issue}")
        return False
    else:
        logger.success("✅ Cleanup verification passed!")
        return True

def create_backup_summary():
    """Create a summary of what was cleared for records"""
    try:
        summary = {
            "cleanup_timestamp": str(Path(__file__).stat().st_mtime),
            "cleanup_script": "complete_fresh_cleanup.py",
            "areas_cleared": [
                "admin_documents table",
                "document_chunks table", 
                "global_vector_store table",
                "uploaded files in backend/uploads/admin_documents/",
                "vector stores in backend/vector_stores/admin_documents/",
                "Redis cache entries",
                "Celery processing tasks"
            ],
            "note": "Complete fresh cleanup performed to resolve document hash conflicts"
        }
        
        summary_file = Path(__file__).parent / "cleanup_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"📋 Cleanup summary saved to {summary_file}")
        
    except Exception as e:
        logger.warning(f"Could not create cleanup summary: {e}")

def main():
    """Main cleanup orchestrator"""
    logger.info("🚨 STARTING COMPLETE FRESH CLEANUP OF ALL ADMIN DOCUMENTS")
    logger.info("This will remove ALL uploaded documents, vector stores, and database records!")
    
    try:
        # Step 1: Clear Redis cache
        logger.info("Step 1: Clearing Redis cache...")
        clear_redis_cache()
        
        # Step 2: Clear Celery tasks  
        logger.info("Step 2: Clearing Celery tasks...")
        clear_celery_tasks()
        
        # Step 3: Clear database records
        logger.info("Step 3: Clearing database records...")
        clear_database_completely()
        
        # Step 4: Clear file storage
        logger.info("Step 4: Clearing file storage...")
        clear_file_storage()
        
        # Step 5: Verify cleanup
        logger.info("Step 5: Verifying cleanup...")
        success = verify_cleanup()
        
        # Step 6: Create summary
        logger.info("Step 6: Creating cleanup summary...")
        create_backup_summary()
        
        if success:
            logger.success("🎉 COMPLETE FRESH CLEANUP SUCCESSFUL!")
            logger.info("💡 You can now upload documents without hash conflicts")
            logger.info("🔄 The system is ready for fresh document uploads")
        else:
            logger.warning("⚠️  Cleanup completed but some issues remain")
            logger.info("🔍 Check the warnings above and consider manual cleanup if needed")
        
    except Exception as e:
        logger.error(f"💥 Cleanup failed: {e}")
        logger.error("❌ Please check the error and try again")
        sys.exit(1)

if __name__ == "__main__":
    # Add confirmation prompt for safety
    print("⚠️  WARNING: This will permanently delete ALL admin documents and vector stores!")
    print("📂 All uploaded files, database records, and vector stores will be removed.")
    print("🔄 This action cannot be undone.")
    
    confirm = input("\n👆 Type 'YES' to confirm complete cleanup: ")
    
    if confirm.strip().upper() == 'YES':
        main()
    else:
        print("❌ Cleanup cancelled")
        sys.exit(0)