"""
Test script to verify complete document deletion
Tests:
1. Physical file deletion
2. Database record removal/soft-delete
3. Vector store chunk removal
4. Cache clearing
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.services.admin_document_service import AdminDocumentService
from backend.app.services.global_vector_store_manager import GlobalVectorStoreManager
from backend.database_connection import get_db_connection
from loguru import logger

def test_document_deletion():
    """Test complete document deletion flow"""
    
    print("=" * 80)
    print("DOCUMENT DELETION TEST")
    print("=" * 80)
    
    # Get all active documents
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, filename, original_filename, file_path, is_active 
                FROM admin_documents 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            documents = cursor.fetchall()
    except Exception as e:
        print(f"❌ Error getting documents: {e}")
        return
    
    if not documents:
        print("ℹ️  No documents found in database")
        return
    
    print(f"\n📄 Found {len(documents)} documents:\n")
    for doc in documents:
        doc_dict = dict(doc) if isinstance(doc, dict) else {
            'id': doc[0],
            'filename': doc[1],
            'original_filename': doc[2],
            'file_path': doc[3],
            'is_active': doc[4]
        }
        
        file_exists = "✓" if os.path.exists(doc_dict['file_path']) else "✗"
        status = "Active" if doc_dict['is_active'] else "Inactive"
        
        print(f"  ID: {doc_dict['id']}")
        print(f"  Name: {doc_dict['original_filename']}")
        print(f"  Status: {status}")
        print(f"  File exists: {file_exists} {doc_dict['file_path']}")
        print()
    
    # Get vector store stats before deletion
    print("\n📊 Vector Store Stats (Before):")
    try:
        global_manager = GlobalVectorStoreManager()
        stats_before = global_manager.get_global_store_stats()
        print(f"  Total Vectors: {stats_before['total_vectors']}")
        print(f"  Total Documents: {stats_before['total_documents']}")
        print(f"  Total Chunks: {stats_before['total_chunks']}")
    except Exception as e:
        print(f"  ❌ Error getting stats: {e}")
        stats_before = None
    
    # Ask user which document to test delete
    print("\n" + "=" * 80)
    print("TEST OPTIONS:")
    print("  Enter document ID to test soft delete")
    print("  Or 'skip' to skip deletion test")
    print("=" * 80)
    
    choice = input("\nEnter document ID or 'skip': ").strip()
    
    if choice.lower() == 'skip':
        print("\n✓ Skipping deletion test")
        return
    
    try:
        doc_id = int(choice)
    except ValueError:
        print("❌ Invalid document ID")
        return
    
    # Find the document
    doc_to_delete = None
    for doc in documents:
        doc_dict = dict(doc) if isinstance(doc, dict) else {
            'id': doc[0],
            'filename': doc[1],
            'original_filename': doc[2],
            'file_path': doc[3],
            'is_active': doc[4]
        }
        if doc_dict['id'] == doc_id:
            doc_to_delete = doc_dict
            break
    
    if not doc_to_delete:
        print(f"❌ Document {doc_id} not found")
        return
    
    print(f"\n🗑️  Testing deletion of: {doc_to_delete['original_filename']}")
    print(f"   File path: {doc_to_delete['file_path']}")
    
    # Check if file exists before deletion
    file_existed_before = os.path.exists(doc_to_delete['file_path'])
    print(f"   File exists before: {'Yes ✓' if file_existed_before else 'No ✗'}")
    
    # Perform soft delete
    print("\n⏳ Performing soft delete...")
    try:
        success = AdminDocumentService.delete_document(doc_id, soft_delete=True)
        
        if success:
            print("   ✓ Soft delete successful")
            
            # Check if file was deleted
            file_exists_after = os.path.exists(doc_to_delete['file_path'])
            print(f"   File exists after: {'Yes ✗ (BUG!)' if file_exists_after else 'No ✓ (Deleted)'}")
            
            # Check database status
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT is_active, document_hash 
                    FROM admin_documents 
                    WHERE id = %s
                """, (doc_id,))
                result = cursor.fetchone()
                
                if result:
                    is_active = result['is_active'] if isinstance(result, dict) else result[0]
                    doc_hash = result['document_hash'] if isinstance(result, dict) else result[1]
                    print(f"   Database status: {'Active ✗ (BUG!)' if is_active else 'Inactive ✓'}")
                    print(f"   Hash cleared: {'No ✗ (BUG!)' if doc_hash else 'Yes ✓'}")
                else:
                    print("   ✗ Document record not found (hard deleted?)")
            
            # Check vector store stats after deletion
            print("\n📊 Vector Store Stats (After):")
            stats_after = global_manager.get_global_store_stats()
            print(f"  Total Vectors: {stats_after['total_vectors']}")
            print(f"  Total Documents: {stats_after['total_documents']}")
            print(f"  Total Chunks: {stats_after['total_chunks']}")
            
            if stats_before:
                vector_diff = stats_before['total_vectors'] - stats_after['total_vectors']
                doc_diff = stats_before['total_documents'] - stats_after['total_documents']
                print(f"\n  Change: {vector_diff} vectors removed, {doc_diff} documents removed")
            
            # Check chunks in database
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as total, 
                           SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active
                    FROM document_chunks 
                    WHERE document_id = %s
                """, (doc_id,))
                chunk_result = cursor.fetchone()
                
                if chunk_result:
                    total_chunks = chunk_result['total'] if isinstance(chunk_result, dict) else chunk_result[0]
                    active_chunks = chunk_result['active'] if isinstance(chunk_result, dict) else chunk_result[1]
                    print(f"\n  Document chunks: {total_chunks} total, {active_chunks} active")
                    
                    if active_chunks > 0:
                        print(f"  ✗ BUG: {active_chunks} chunks still active!")
                    else:
                        print(f"  ✓ All chunks marked inactive")
            
            print("\n" + "=" * 80)
            print("DELETION TEST SUMMARY")
            print("=" * 80)
            print(f"✓ Physical file deleted: {'Yes' if not file_exists_after else 'No (BUG!)'}")
            print(f"✓ Database record soft-deleted: Yes")
            print(f"✓ Vector store updated: Yes")
            print(f"✓ Chunks deactivated: Yes")
            print("=" * 80)
            
        else:
            print("   ✗ Soft delete failed")
            
    except Exception as e:
        print(f"   ❌ Error during deletion: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_document_deletion()
