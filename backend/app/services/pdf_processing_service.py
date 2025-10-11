"""
PDF Processing Service - Backend server processing replacement for Celery
Handles PDF document processing in background threads
"""
import os
import logging
from typing import Dict, Any
from pathlib import Path
from loguru import logger

from .background_task_service import background_service
from .admin_document_service import AdminDocumentService
from .task_service import TaskService
from .rag_service import DocumentProcessor
from .dual_embedding_manager import EmbeddingManager
from .rag_handler import clear_global_cache
from ...database_connection import get_db_connection
from ...vector_store_db import save_vector_store_path

class PDFProcessingService:
    def __init__(self):
        # Register handlers with background service
        background_service.register_handler("process_pdf", self.process_pdf_task)
        background_service.register_handler("process_admin_pdf", self.process_admin_pdf_task)
    
    def queue_pdf_processing(self, user_id: int, file_path: str, filename: str) -> str:
        """Queue a PDF for user processing"""
        task_id = background_service.add_task(
            task_type="process_pdf",
            data={
                "user_id": user_id,
                "file_path": file_path,
                "filename": filename
            }
        )
        
        # Store task in database for tracking
        TaskService.store_user_task(user_id, task_id, "pdf_processing", filename)
        
        logger.info(f"Queued PDF processing for user {user_id}: {filename}")
        return task_id
    
    def queue_admin_pdf_processing(self, document_id: int, file_path: str, filename: str) -> str:
        """Queue a PDF for admin processing"""
        task_id = background_service.add_task(
            task_type="process_admin_pdf",
            data={
                "document_id": document_id,
                "file_path": file_path,
                "filename": filename
            }
        )
        
        logger.info(f"Queued admin PDF processing for document {document_id}: {filename}")
        return task_id
    
    def process_pdf_task(self, task, user_id: int, file_path: str, filename: str):
        """Process a PDF file for regular user (replaces process_pdf_task)"""
        task_id = task.request.id
        
        logger.info(f"Starting PDF processing task for user {user_id}")
        logger.info(f"📋 Task ID: {task_id}")
        logger.info(f"📄 File: {filename}")
        logger.info(f"📂 Path: {file_path}")
        
        try:
            # Validate file exists before processing
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")
            
            # Update task status
            background_service.update_task_progress(task_id, 10, "Starting PDF processing...")
            TaskService.update_task_status(task_id, 'processing', 'Starting PDF processing...')
            
            processor = DocumentProcessor()
            
            # Extract text from PDF
            logger.info("Loading and extracting text from PDF...")
            background_service.update_task_progress(task_id, 30, "Loading and extracting text from PDF...")
            TaskService.update_task_status(task_id, 'processing', 'Loading and extracting text from PDF...')
            
            page_texts, language = processor.process_pdf(file_path, filename)
            total_chars = sum(len(page['text']) for page in page_texts)
            logger.info(f"PDF text extracted successfully - {total_chars} characters from {len(page_texts)} pages, Language: {language}")
            
            # Split text into chunks
            logger.info(f"Splitting {language} text into chunks...")
            background_service.update_task_progress(task_id, 50, f"Splitting {language} text into chunks...")
            TaskService.update_task_status(task_id, 'processing', f'Splitting {language} text into chunks...')
            chunks_with_metadata = processor.split_text_with_metadata(page_texts)
            logger.info(f"Text split into {len(chunks_with_metadata)} chunks for {language} processing")
            
            # Create embeddings and vector store
            logger.info(f"Creating {language} embeddings...")
            background_service.update_task_progress(task_id, 70, f"Creating {language} embeddings...")
            TaskService.update_task_status(task_id, 'processing', f'Creating {language} embeddings...')
            vector_store = processor.create_vector_store_with_metadata(chunks_with_metadata, language)
            logger.info(f"Vector store created with {vector_store.index.ntotal} vectors using {language} embeddings")

            vector_store_dir = os.path.join(processor.vector_store_dir, f"user_{user_id}")
            os.makedirs(vector_store_dir, exist_ok=True)
            
            # Save vector store
            logger.info(f"Saving {language} vector store...")
            background_service.update_task_progress(task_id, 85, "Saving vector store...")
            TaskService.update_task_status(task_id, 'processing', 'Saving vector store...')
            
            vector_store_path = os.path.join(vector_store_dir, "current_pdf")
            vector_store.save_local(vector_store_path, index_name="index")
            
            if not os.path.exists(os.path.join(vector_store_path, "index.faiss")):
                raise Exception("Vector store files not created properly")
                
            logger.info(f"Vector store saved to: {vector_store_path}")

            # Update database
            logger.info("Finalizing database update with language information...")
            background_service.update_task_progress(task_id, 95, "Finalizing...")
            TaskService.update_task_status(task_id, 'processing', 'Finalizing...')

            embedding_model = EmbeddingManager.MODEL

            with get_db_connection() as conn:
                save_vector_store_path(conn, user_id, vector_store_path, language, embedding_model)

            # Mark task as completed
            background_service.update_task_progress(task_id, 100, f"{language.title()} PDF processed successfully")
            TaskService.update_task_status(task_id, 'completed', f'{language.title()} PDF processed successfully')

            logger.info(f"{language.title()} PDF processing completed successfully for user {user_id}")
            logger.info(f"Final stats: {vector_store.index.ntotal} vectors, {len(chunks_with_metadata)} chunks, Language: {language}")

            return {
                'status': 'completed',
                'message': f'{language.title()} PDF processed successfully',
                'vector_count': vector_store.index.ntotal,
                'language': language,
                'embedding_model': embedding_model,
                'chunks_count': len(chunks_with_metadata)
            }
            
        except Exception as e:
            error_msg = f"Error in PDF processing task: {str(e)}"
            logger.error(f"{error_msg}")
            logger.exception("Full error traceback:")
            
            # Update task status in database
            try:
                TaskService.update_task_status(task_id, 'failed', str(e))
            except Exception as db_error:
                logger.error(f"Failed to update task status: {db_error}")
            
            # Re-raise the exception
            raise Exception(error_msg)
    
    def process_admin_pdf_task(self, task, document_id: int, file_path: str, filename: str):
        """Process PDF for admin global knowledge base (replaces process_admin_pdf_task)"""
        task_id = task.request.id
        
        logger.info(f"Starting admin PDF processing task for document {document_id}")
        logger.info(f"📋 Task ID: {task_id}")
        logger.info(f"📄 File: {filename}")
        logger.info(f"📂 Path: {file_path}")
        
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")
            
            # Update task and document status
            background_service.update_task_progress(task_id, 10, "Starting admin PDF processing...")
            TaskService.update_task_status(task_id, 'processing', 'Starting admin PDF processing...')
            AdminDocumentService.update_document_processing_status(document_id, 'processing')
            
            processor = DocumentProcessor()
            
            # Extract and process PDF
            logger.info("Loading and extracting text from admin PDF...")
            background_service.update_task_progress(task_id, 30, "Loading and extracting text...")
            TaskService.update_task_status(task_id, 'processing', 'Loading and extracting text...')
            
            page_texts, language = processor.process_pdf(file_path, filename)
            total_chars = sum(len(page['text']) for page in page_texts)
            logger.info(f"Admin PDF text extracted - {total_chars} characters from {len(page_texts)} pages, Language: {language}")
            
            # Split text into chunks
            logger.info(f"Splitting {language} text into chunks...")
            background_service.update_task_progress(task_id, 50, f"Splitting {language} text into chunks...")
            TaskService.update_task_status(task_id, 'processing', f'Splitting {language} text into chunks...')
            chunks_with_metadata = processor.split_text_with_metadata(page_texts)
            logger.info(f"Text split into {len(chunks_with_metadata)} chunks for admin document")
            
            # Add directly to global vector store
            logger.info("Adding chunks directly to global vector store...")
            background_service.update_task_progress(task_id, 70, "Adding to global vector store...")
            TaskService.update_task_status(task_id, 'processing', 'Adding to global vector store...')
            
            from .global_vector_store_manager import GlobalVectorStoreManager
            global_manager = GlobalVectorStoreManager()
            
            success = global_manager.add_document_to_global_store(document_id, chunks_with_metadata)
            
            if not success:
                raise Exception("Failed to add document to global vector store")
            
            # Get updated stats
            stats = global_manager.get_global_store_stats()
            logger.info(f"Global vector store updated - Total vectors: {stats['total_vectors']}, Total documents: {stats['total_documents']}")

            # Update database records
            logger.info("Finalizing admin document processing...")
            background_service.update_task_progress(task_id, 90, "Finalizing admin document...")
            TaskService.update_task_status(task_id, 'processing', 'Finalizing admin document...')

            embedding_model = EmbeddingManager.MODEL

            # Update admin document record with text preview
            extracted_text = "\n".join([page['text'] for page in page_texts])
            text_preview = extracted_text[:1000] if len(extracted_text) > 1000 else extracted_text
            AdminDocumentService.update_document_processing_status(
                document_id, 
                'completed', 
                stats['store_path'], 
                language,
                task_id=task_id,
                text_content=text_preview
            )            # Clear global cache so users get the new document immediately
            clear_global_cache()
            logger.info("Cleared global cache after admin document processing")

            # Mark task as completed
            background_service.update_task_progress(task_id, 100, f"Admin {language.title()} PDF processed successfully")
            TaskService.update_task_status(task_id, 'completed', f'Admin {language.title()} PDF processed successfully')

            logger.info(f"Admin PDF processing completed successfully for document {document_id}")
            logger.info(f"Final stats - Global vectors: {stats['total_vectors']}, Document chunks: {len(chunks_with_metadata)}, Language: {language}")

            return {
                'status': 'completed',
                'message': f'Admin {language.title()} PDF processed successfully',
                'document_id': document_id,
                'global_vector_count': stats['total_vectors'],
                'document_chunks': len(chunks_with_metadata),
                'language': language,
                'embedding_model': embedding_model,
                'total_documents': stats['total_documents']
            }
            
        except Exception as e:
            error_msg = f"Error in admin PDF processing task: {str(e)}"
            logger.error(f"{error_msg}")
            logger.exception("Full admin task error traceback:")
            
            # Update task and document status with error message
            try:
                TaskService.update_task_status(task_id, 'failed', str(e))
                AdminDocumentService.update_document_processing_status(
                    document_id, 
                    'failed',
                    task_id=task_id,
                    error_message=str(e)
                )
            except Exception as db_error:
                logger.error(f"Failed to update admin task status: {db_error}")
            
            raise Exception(error_msg)

# Global instance
pdf_processing_service = PDFProcessingService()