"""
Admin Document Service - Manages persistent document storage for admin users
"""
from typing import List, Optional, Dict
import sys
import os

# Add backend directory to path for direct execution
if __name__ == "__main__" or not __package__:
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sys.path.insert(0, backend_dir)
    from database_connection import get_db_connection
    from schemas import AdminDocument, AdminDocumentResponse, AdminDocumentsListResponse
else:
    from ...database_connection import get_db_connection
    from ...schemas import AdminDocument, AdminDocumentResponse, AdminDocumentsListResponse

import hashlib
import json
from datetime import datetime
from loguru import logger
from psycopg2.extras import Json

class AdminDocumentService:
    """Service for managing admin documents and global vector store"""
    
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    @staticmethod
    def document_exists_by_hash(document_hash: str) -> bool:
        """Check if document already exists by hash"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM admin_documents 
                    WHERE document_hash = %s AND is_active = true
                    LIMIT 1
                """, (document_hash,))
                
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking document hash: {str(e)}")
            return False
    
    @staticmethod
    def create_admin_document(
        filename: str,
        original_filename: str,
        file_path: str,
        uploaded_by: int,
        file_size: int = None
    ) -> Dict:
        """Create new admin document record"""
        try:
            # Calculate file hash
            document_hash = AdminDocumentService.calculate_file_hash(file_path)
            
            # Check for duplicates
            if AdminDocumentService.document_exists_by_hash(document_hash):
                raise ValueError("Document with identical content already exists")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO admin_documents 
                    (filename, original_filename, file_path, file_size, document_hash, uploaded_by, processing_status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                    RETURNING *
                """, (filename, original_filename, file_path, file_size, document_hash, uploaded_by))
                
                result = cursor.fetchone()
                conn.commit()
                
                logger.info(f"Created admin document record: {filename}")
                return dict(result)
                
        except Exception as e:
            logger.error(f"Error creating admin document: {str(e)}")
            raise
    
    @staticmethod
    def update_document_processing_status(
        document_id: int, 
        status: str, 
        vector_store_path: str = None,
        language: str = None
    ) -> bool:
        """Update document processing status"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                update_fields = ["processing_status = %s", "updated_at = CURRENT_TIMESTAMP"]
                values = [status]
                
                if vector_store_path:
                    update_fields.append("vector_store_path = %s")
                    values.append(vector_store_path)
                    
                if language:
                    update_fields.append("language = %s")
                    values.append(language)
                
                values.append(document_id)
                
                query = f"""
                    UPDATE admin_documents 
                    SET {', '.join(update_fields)}
                    WHERE id = %s
                """
                
                cursor.execute(query, values)
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating document status: {str(e)}")
            return False
    
    @staticmethod
    def get_all_active_documents() -> List[Dict]:
        """Get all active admin documents"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, filename, original_filename, file_size, processing_status, 
                           language, created_at, updated_at, is_active
                    FROM admin_documents 
                    WHERE is_active = true
                    ORDER BY created_at DESC
                """)
                
                documents = cursor.fetchall()
                return [dict(doc) for doc in documents]
                
        except Exception as e:
            logger.error(f"Error fetching admin documents: {str(e)}")
            return []
    
    @staticmethod
    def get_documents_by_status(status: str) -> List[Dict]:
        """Get documents by processing status"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM admin_documents 
                    WHERE processing_status = %s AND is_active = true
                    ORDER BY created_at DESC
                """, (status,))
                
                documents = cursor.fetchall()
                return [dict(doc) for doc in documents]
                
        except Exception as e:
            logger.error(f"Error fetching documents by status: {str(e)}")
            return []
    
    @staticmethod
    def get_completed_documents() -> List[Dict]:
        """Get all completed/processed documents"""
        return AdminDocumentService.get_documents_by_status('completed')
    
    @staticmethod
    def get_document_by_id(document_id: int) -> Optional[Dict]:
        """Get document by ID"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM admin_documents 
                    WHERE id = %s AND is_active = true
                """, (document_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Error fetching document: {str(e)}")
            return None
    
    @staticmethod
    def delete_document(document_id: int, soft_delete: bool = True) -> bool:
        """Delete or soft delete document"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                if soft_delete:
                    cursor.execute("""
                        UPDATE admin_documents 
                        SET is_active = false, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (document_id,))
                else:
                    cursor.execute("DELETE FROM admin_documents WHERE id = %s", (document_id,))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            return False
    
    @staticmethod
    def get_documents_summary() -> Dict:
        """Get summary of document statistics"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get total and active counts
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN is_active = true THEN 1 END) as active,
                        COUNT(CASE WHEN processing_status = 'completed' AND is_active = true THEN 1 END) as completed,
                        COUNT(CASE WHEN processing_status = 'processing' AND is_active = true THEN 1 END) as processing,
                        COUNT(CASE WHEN processing_status = 'failed' AND is_active = true THEN 1 END) as failed
                    FROM admin_documents
                """)
                
                result = cursor.fetchone()
                return dict(result) if result else {}
                
        except Exception as e:
            logger.error(f"Error getting documents summary: {str(e)}")
            return {}

class GlobalVectorStoreService:
    """Service for managing global vector store with document chunk tracking"""
    
    @staticmethod
    def create_document_chunks_table():
        """Create table to track document chunks in global vector store"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Create document_chunks table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        id SERIAL PRIMARY KEY,
                        document_id INTEGER NOT NULL REFERENCES admin_documents(id) ON DELETE CASCADE,
                        chunk_index INTEGER NOT NULL,
                        chunk_text TEXT NOT NULL,
                        metadata JSONB,
                        vector_index INTEGER, -- Index position in FAISS vector store
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT true
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id 
                    ON document_chunks(document_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_document_chunks_active 
                    ON document_chunks(document_id, is_active)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_document_chunks_vector_index 
                    ON document_chunks(vector_index)
                """)
                
                conn.commit()
                logger.info("Document chunks table created successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error creating document chunks table: {str(e)}")
            return False
    
    @staticmethod
    def add_document_to_global_store(document_id: int, vector_store_path: str, chunk_count: int = 0) -> bool:
        """Add document to global vector store (legacy method for compatibility)"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # First check if record exists
                cursor.execute("SELECT id FROM global_vector_store WHERE document_id = %s", (document_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute("""
                        UPDATE global_vector_store 
                        SET vector_store_path = %s, chunk_count = %s, is_active = true, created_at = NOW()
                        WHERE document_id = %s
                    """, (vector_store_path, chunk_count, document_id))
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO global_vector_store (document_id, vector_store_path, chunk_count, created_at, is_active)
                        VALUES (%s, %s, %s, NOW(), true)
                    """, (document_id, vector_store_path, chunk_count))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error adding to global vector store: {str(e)}")
            return False
            
    @staticmethod
    def add_document_chunks(document_id: int, chunks_with_metadata: list, start_vector_index: int = 0) -> bool:
        """Add document chunks to the tracking table"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Insert all chunks for this document
                for i, chunk_data in enumerate(chunks_with_metadata):
                    # Use psycopg2.extras.Json to properly handle dict for JSONB field
                    metadata = chunk_data.get('metadata', {})
                    
                    # Clean the text to remove null bytes and other problematic characters
                    chunk_text = chunk_data['text']
                    if chunk_text:
                        # Remove null bytes and other control characters that PostgreSQL can't handle
                        chunk_text = chunk_text.replace('\x00', '').replace('\0', '')
                        # Also remove other common problematic characters
                        chunk_text = ''.join(char for char in chunk_text if ord(char) >= 32 or char in '\t\n\r')
                    
                    cursor.execute("""
                        INSERT INTO document_chunks 
                        (document_id, chunk_index, chunk_text, metadata, vector_index, created_at, is_active)
                        VALUES (%s, %s, %s, %s, %s, NOW(), true)
                    """, (
                        document_id,
                        i,
                        chunk_text,  # Use cleaned text
                        Json(metadata),  # Use Json adapter for proper JSONB handling
                        start_vector_index + i
                    ))
                
                conn.commit()
                logger.info(f"Added {len(chunks_with_metadata)} chunks for document {document_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error adding document chunks: {str(e)}")
            return False
    
    @staticmethod
    def remove_document_from_global_store(document_id: int) -> Dict:
        """Remove document and its chunks from global vector store"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get chunk information before deletion
                cursor.execute("""
                    SELECT vector_index, chunk_index
                    FROM document_chunks 
                    WHERE document_id = %s AND is_active = true
                    ORDER BY vector_index
                """, (document_id,))
                
                chunks_to_remove = cursor.fetchall()
                
                if not chunks_to_remove:
                    logger.warning(f"No chunks found for document {document_id}")
                    return {'removed_chunks': 0, 'vector_indices': []}
                
                # Mark chunks as inactive
                cursor.execute("""
                    UPDATE document_chunks 
                    SET is_active = false 
                    WHERE document_id = %s
                """, (document_id,))
                
                # Mark global vector store record as inactive
                cursor.execute("""
                    UPDATE global_vector_store 
                    SET is_active = false 
                    WHERE document_id = %s
                """, (document_id,))
                
                conn.commit()
                
                vector_indices = [chunk[0] for chunk in chunks_to_remove]
                logger.info(f"Marked {len(chunks_to_remove)} chunks as inactive for document {document_id}")
                
                return {
                    'removed_chunks': len(chunks_to_remove),
                    'vector_indices': vector_indices
                }
                
        except Exception as e:
            logger.error(f"Error removing document from global store: {str(e)}")
            return {'removed_chunks': 0, 'vector_indices': []}
    
    @staticmethod
    def get_active_document_chunks(document_id: int = None) -> List[Dict]:
        """Get active chunks for a specific document or all documents"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                if document_id:
                    cursor.execute("""
                        SELECT dc.*, ad.filename, ad.original_filename
                        FROM document_chunks dc
                        JOIN admin_documents ad ON dc.document_id = ad.id
                        WHERE dc.document_id = %s AND dc.is_active = true AND ad.is_active = true
                        ORDER BY dc.vector_index
                    """, (document_id,))
                else:
                    cursor.execute("""
                        SELECT dc.*, ad.filename, ad.original_filename
                        FROM document_chunks dc
                        JOIN admin_documents ad ON dc.document_id = ad.id
                        WHERE dc.is_active = true AND ad.is_active = true
                        ORDER BY dc.document_id, dc.vector_index
                    """)
                
                chunks = cursor.fetchall()
                return [dict(chunk) for chunk in chunks]
                
        except Exception as e:
            logger.error(f"Error fetching document chunks: {str(e)}")
            return []
    
    @staticmethod
    def get_global_chunk_count() -> int:
        """Get total count of active chunks in global vector store"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM document_chunks dc
                    JOIN admin_documents ad ON dc.document_id = ad.id
                    WHERE dc.is_active = true AND ad.is_active = true
                """)
                
                count = cursor.fetchone()[0]
                return count or 0
                
        except Exception as e:
            logger.error(f"Error getting global chunk count: {str(e)}")
            return 0
    
    @staticmethod
    def get_active_vector_stores() -> List[Dict]:
        """Get all active vector stores for global knowledge base"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT gvs.*, ad.filename, ad.language, ad.embedding_model
                    FROM global_vector_store gvs
                    JOIN admin_documents ad ON gvs.document_id = ad.id
                    WHERE gvs.is_active = true AND ad.is_active = true
                    ORDER BY gvs.created_at DESC
                """)
                
                stores = cursor.fetchall()
                return [dict(store) for store in stores]
                
        except Exception as e:
            logger.error(f"Error fetching active vector stores: {str(e)}")
            return []
    
    @staticmethod
    def get_global_knowledge_stats() -> Dict:
        """Get statistics about global knowledge base"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_documents,
                        SUM(chunk_count) as total_chunks,
                        COUNT(DISTINCT ad.language) as languages_count
                    FROM global_vector_store gvs
                    JOIN admin_documents ad ON gvs.document_id = ad.id
                    WHERE gvs.is_active = true AND ad.is_active = true
                """)
                
                result = cursor.fetchone()
                return dict(result) if result else {}
                
        except Exception as e:
            logger.error(f"Error getting global knowledge stats: {str(e)}")
            return {}