"""
Global Vector Store Manager - Manages a single global vector store for all admin documents
"""
import os
import json
from typing import List, Dict, Optional
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from loguru import logger

from ..services.dual_embedding_manager import EmbeddingManager
from ..services.admin_document_service import GlobalVectorStoreService
from ...database_connection import get_db_connection

class GlobalVectorStoreManager:
    """Manager for the single global vector store containing all admin documents"""
    
    def __init__(self):
        self.vector_store_dir = os.path.join(
            os.path.dirname(__file__), 
            '../../vector_stores/admin_documents'
        )
        os.makedirs(self.vector_store_dir, exist_ok=True)
        self.global_store_path = os.path.join(self.vector_store_dir, "global_knowledge_base")
        
        # Ensure document_chunks table exists
        GlobalVectorStoreService.create_document_chunks_table()
    
    def _load_or_create_global_store(self) -> FAISS:
        """Load existing global store or create new empty one"""
        try:
            embeddings = EmbeddingManager.get_embeddings_static()
            
            # Check if global store exists
            index_file = os.path.join(self.global_store_path, "index.faiss")
            pkl_file = os.path.join(self.global_store_path, "index.pkl")
            
            if os.path.exists(index_file) and os.path.exists(pkl_file):
                # Load existing store
                vectorstore = FAISS.load_local(
                    self.global_store_path,
                    embeddings,
                    index_name="index",
                    allow_dangerous_deserialization=True
                )
                logger.info(f"Loaded existing global vector store with {vectorstore.index.ntotal} vectors")
                return vectorstore
            else:
                # Create new empty store
                logger.info("Creating new global vector store")
                # Create with a dummy document
                dummy_texts = ["Initializing global vector store"]
                dummy_metadatas = [{"document": "system", "temporary": True}]
                
                vectorstore = FAISS.from_texts(
                    dummy_texts,
                    embeddings,
                    metadatas=dummy_metadatas
                )
                
                # Save the empty store
                vectorstore.save_local(self.global_store_path, index_name="index")
                logger.info("Created new global vector store")
                return vectorstore
                
        except Exception as e:
            logger.error(f"Error loading/creating global vector store: {e}")
            raise
    
    def add_document_to_global_store(self, document_id: int, chunks_with_metadata: List[Dict]) -> bool:
        """Add a document's chunks directly to the global vector store"""
        try:
            if not chunks_with_metadata:
                logger.warning(f"No chunks provided for document {document_id}")
                return False
            
            # Load the global store
            global_store = self._load_or_create_global_store()
            current_vector_count = global_store.index.ntotal
            
            # Add document metadata to each chunk
            enriched_chunks = []
            texts = []
            metadatas = []
            
            for i, chunk_data in enumerate(chunks_with_metadata):
                # Enrich metadata with document information
                metadata = chunk_data.get('metadata', {}).copy()
                metadata['document_id'] = document_id
                metadata['chunk_index'] = i
                metadata['global_chunk_id'] = f"doc_{document_id}_chunk_{i}"
                
                enriched_chunks.append({
                    'text': chunk_data['text'],
                    'metadata': metadata
                })
                
                texts.append(chunk_data['text'])
                metadatas.append(metadata)
            
            # Add new texts to the global store
            global_store.add_texts(texts, metadatas=metadatas)
            
            # Save the updated global store
            global_store.save_local(self.global_store_path, index_name="index")
            
            logger.info(f"Added {len(chunks_with_metadata)} chunks from document {document_id} to global store")
            logger.info(f"Global store now has {global_store.index.ntotal} total vectors")
            
            # Track chunks in database
            success = GlobalVectorStoreService.add_document_chunks(
                document_id, 
                enriched_chunks, 
                current_vector_count
            )
            
            if not success:
                logger.error(f"Failed to track chunks in database for document {document_id}")
                return False
            
            # Update global vector store record
            GlobalVectorStoreService.add_document_to_global_store(
                document_id,
                self.global_store_path,
                len(chunks_with_metadata)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding document {document_id} to global store: {e}")
            return False
    
    def remove_document_from_global_store(self, document_id: int) -> bool:
        """Remove a document's chunks from the global vector store"""
        try:
            # Get chunk information
            removal_info = GlobalVectorStoreService.remove_document_from_global_store(document_id)
            
            if removal_info['removed_chunks'] == 0:
                logger.warning(f"No chunks found to remove for document {document_id}")
                return True
            
            logger.info(f"Marked {removal_info['removed_chunks']} chunks as inactive for document {document_id}")
            
            # Rebuild the global vector store without inactive chunks
            success = self._rebuild_global_store()
            
            if success:
                logger.success(f"Successfully removed document {document_id} from global store")
            else:
                logger.error(f"Failed to rebuild global store after removing document {document_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error removing document {document_id} from global store: {e}")
            return False
    
    def _rebuild_global_store(self) -> bool:
        """Rebuild the global vector store using only active chunks"""
        try:
            logger.info("Rebuilding global vector store with only active chunks...")
            
            # Get all active chunks
            active_chunks = GlobalVectorStoreService.get_active_document_chunks()
            
            if not active_chunks:
                logger.info("No active chunks found, creating empty global store")
                # Create empty store
                embeddings = EmbeddingManager.get_embeddings_static()
                dummy_texts = ["Empty global vector store"]
                dummy_metadatas = [{"document": "system", "temporary": True}]
                
                empty_store = FAISS.from_texts(dummy_texts, embeddings, metadatas=dummy_metadatas)
                empty_store.save_local(self.global_store_path, index_name="index")
                
                return True
            
            # Rebuild from active chunks
            texts = []
            metadatas = []
            
            for chunk in active_chunks:
                texts.append(chunk['chunk_text'])
                
                # Parse metadata from JSONB
                metadata = chunk.get('metadata', {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                # Ensure document_id is in metadata
                metadata['document_id'] = chunk['document_id']
                metadata['chunk_index'] = chunk['chunk_index']
                metadata['global_chunk_id'] = f"doc_{chunk['document_id']}_chunk_{chunk['chunk_index']}"
                metadata['filename'] = chunk.get('filename', 'Unknown')
                
                metadatas.append(metadata)
            
            # Create new global store
            embeddings = EmbeddingManager.get_embeddings_static()
            new_global_store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
            
            # Save the rebuilt store
            new_global_store.save_local(self.global_store_path, index_name="index")
            
            # Update vector indices in database
            self._update_chunk_vector_indices(active_chunks)
            
            logger.success(f"Rebuilt global vector store with {len(active_chunks)} active chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error rebuilding global vector store: {e}")
            return False
    
    def _update_chunk_vector_indices(self, chunks: List[Dict]) -> bool:
        """Update vector indices in database after rebuild"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                for i, chunk in enumerate(chunks):
                    cursor.execute("""
                        UPDATE document_chunks 
                        SET vector_index = %s 
                        WHERE id = %s
                    """, (i, chunk['id']))
                
                conn.commit()
                logger.info(f"Updated vector indices for {len(chunks)} chunks")
                return True
                
        except Exception as e:
            logger.error(f"Error updating chunk vector indices: {e}")
            return False
    
    def get_global_store_stats(self) -> Dict:
        """Get statistics about the global vector store"""
        try:
            # Get vector store info
            index_file = os.path.join(self.global_store_path, "index.faiss")
            vector_count = 0
            
            if os.path.exists(index_file):
                global_store = self._load_or_create_global_store()
                vector_count = global_store.index.ntotal
            
            # Get database stats
            chunk_count = GlobalVectorStoreService.get_global_chunk_count()
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get document count
                cursor.execute("""
                    SELECT COUNT(DISTINCT document_id) 
                    FROM document_chunks dc
                    JOIN admin_documents ad ON dc.document_id = ad.id
                    WHERE dc.is_active = true AND ad.is_active = true
                """)
                doc_count = cursor.fetchone()[0] or 0
            
            return {
                'total_vectors': vector_count,
                'total_chunks': chunk_count,
                'total_documents': doc_count,
                'store_path': self.global_store_path,
                'store_exists': os.path.exists(index_file)
            }
            
        except Exception as e:
            logger.error(f"Error getting global store stats: {e}")
            return {
                'total_vectors': 0,
                'total_chunks': 0,
                'total_documents': 0,
                'store_path': self.global_store_path,
                'store_exists': False,
                'error': str(e)
            }
    
    def get_document_list(self) -> List[Dict]:
        """Get list of all documents in the global store"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT DISTINCT 
                        ad.id,
                        ad.filename,
                        ad.original_filename,
                        ad.file_size,
                        ad.created_at,
                        ad.language,
                        COUNT(dc.id) as chunk_count
                    FROM admin_documents ad
                    JOIN document_chunks dc ON ad.id = dc.document_id
                    WHERE ad.is_active = true AND dc.is_active = true
                    GROUP BY ad.id, ad.filename, ad.original_filename, ad.file_size, ad.created_at, ad.language
                    ORDER BY ad.created_at DESC
                """)
                
                documents = cursor.fetchall()
                return [dict(doc) for doc in documents]
                
        except Exception as e:
            logger.error(f"Error getting document list: {e}")
            return []
    
    def get_vectorstore(self) -> Optional[FAISS]:
        """Get the global vector store for querying"""
        try:
            return self._load_or_create_global_store()
        except Exception as e:
            logger.error(f"Error getting vectorstore: {e}")
            return None
    
    def rebuild_entire_global_store(self) -> bool:
        """Completely rebuild the global store (maintenance operation)"""
        try:
            logger.info("Starting complete rebuild of global vector store...")
            
            # Remove existing store files
            if os.path.exists(self.global_store_path):
                import shutil
                shutil.rmtree(self.global_store_path)
                logger.info("Removed existing global store files")
            
            # Rebuild from database
            success = self._rebuild_global_store()
            
            if success:
                logger.success("Complete rebuild of global vector store successful")
            else:
                logger.error("Failed to rebuild global vector store")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in complete rebuild: {e}")
            return False