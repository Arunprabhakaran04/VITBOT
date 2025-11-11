"""
Cleanup Script - Delete ALL documents from database and local storage
WARNING: This will permanently delete all admin documents!
"""
import os
import sys
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.services.admin_document_service import AdminDocumentService
from backend.app.services.global_vector_store_manager import GlobalVectorStoreManager
from backend.database_connection import get_db_connection
from backend.app.services.rag_handler import clear_global_cache
from loguru import logger

def cleanup_all_documents():
    """Delete all documents and reset the system"""
    
    print("=" * 80)
    print("⚠️  CLEANUP ALL DOCUMENTS - WARNING")
    print("=" * 80)
    print("\nThis will PERMANENTLY delete:")
    print("  • All PDF files from uploads/admin_documents/")
    print("  • All database records from admin_documents table")
    print("  • All database records from document_chunks table")
    print("  • All vector store files")
    print("  • All cached data")
    print("\n⚠️  THIS CANNOT BE UNDONE! ⚠️")
    print("=" * 80)
    
    confirmation = input("\nType 'DELETE ALL' to confirm: ").strip()
    
    if confirmation != "DELETE ALL":
        print("\n❌ Cleanup cancelled")
        return
    
    print("\n🗑️  Starting cleanup process...\n")
    
    # Step 1: Get all documents
    print("📋 Step 1: Getting all documents...")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, filename, original_filename, file_path 
                FROM admin_documents
            """)
            documents = cursor.fetchall()
            
        doc_count = len(documents)
        print(f"   Found {doc_count} documents to delete\n")
        
    except Exception as e:
        print(f"   ❌ Error getting documents: {e}")
        return
    
    # Step 2: Delete physical files
    print("🗂️  Step 2: Deleting physical files...")
    deleted_files = 0
    for doc in documents:
        doc_dict = dict(doc) if isinstance(doc, dict) else {
            'id': doc[0],
            'filename': doc[1],
            'original_filename': doc[2],
            'file_path': doc[3]
        }
        
        file_path = doc_dict['file_path']
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                deleted_files += 1
                print(f"   ✓ Deleted: {doc_dict['original_filename']}")
            except Exception as e:
                print(f"   ✗ Failed to delete {doc_dict['original_filename']}: {e}")
    
    print(f"\n   Deleted {deleted_files}/{doc_count} physical files\n")
    
    # Step 3: Delete all document_chunks records
    print("🔢 Step 3: Deleting all document chunks...")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM document_chunks")
            chunks_deleted = cursor.rowcount
            conn.commit()
            print(f"   ✓ Deleted {chunks_deleted} chunk records\n")
    except Exception as e:
        print(f"   ❌ Error deleting chunks: {e}\n")
    
    # Step 4: Delete all admin_documents records
    print("📄 Step 4: Deleting all admin document records...")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admin_documents")
            docs_deleted = cursor.rowcount
            conn.commit()
            print(f"   ✓ Deleted {docs_deleted} document records\n")
    except Exception as e:
        print(f"   ❌ Error deleting documents: {e}\n")
    
    # Step 5: Delete vector store files
    print("🗃️  Step 5: Deleting vector store files...")
    try:
        vector_store_base = os.path.join(
            os.path.dirname(__file__),
            'app/services/../../vector_stores'
        )
        
        # Delete admin_documents vector store
        admin_vector_path = os.path.join(vector_store_base, 'admin_documents')
        if os.path.exists(admin_vector_path):
            shutil.rmtree(admin_vector_path)
            print(f"   ✓ Deleted vector store directory: {admin_vector_path}")
        
        # Recreate empty directory
        os.makedirs(admin_vector_path, exist_ok=True)
        print(f"   ✓ Created fresh vector store directory\n")
        
    except Exception as e:
        print(f"   ⚠️  Error deleting vector store: {e}\n")
    
    # Step 6: Clear all caches
    print("🧹 Step 6: Clearing all caches...")
    try:
        clear_global_cache()
        print("   ✓ Cleared global cache\n")
    except Exception as e:
        print(f"   ⚠️  Error clearing cache: {e}\n")
    
    # Step 7: Verify cleanup
    print("✅ Step 7: Verifying cleanup...")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM admin_documents")
            doc_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            chunk_count = cursor.fetchone()[0]
            
        print(f"   Documents remaining: {doc_count}")
        print(f"   Chunks remaining: {chunk_count}")
        
        # Check upload directory
        upload_dir = os.path.join(
            os.path.dirname(__file__),
            'app/routers/../../uploads/admin_documents'
        )
        if os.path.exists(upload_dir):
            files_remaining = len([f for f in os.listdir(upload_dir) if f.endswith('.pdf')])
            print(f"   Files remaining in uploads: {files_remaining}")
        
        if doc_count == 0 and chunk_count == 0:
            print("\n   ✅ Cleanup successful! Database is clean.\n")
        else:
            print("\n   ⚠️  Some records remain in database.\n")
            
    except Exception as e:
        print(f"   ❌ Error verifying cleanup: {e}\n")
    
    print("=" * 80)
    print("🎉 CLEANUP COMPLETED")
    print("=" * 80)
    print("\nYou can now start fresh by uploading new documents!")
    print("The system has been reset to initial state.\n")

if __name__ == "__main__":
    cleanup_all_documents()
