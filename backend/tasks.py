from celery import current_task
from .celery_app import celery_app
from .app.services.rag_service import DocumentProcessor
from .app.services.dual_embedding_manager import EmbeddingManager
from .app.services.task_service import TaskService
from .app.services.admin_document_service import AdminDocumentService, GlobalVectorStoreService
from .app.services.rag_handler import clear_global_cache
from .database_connection import get_db_connection
from .vector_store_db import save_vector_store_path
from langchain_community.vectorstores import FAISS
from loguru import logger
import os

@celery_app.task(bind=True)
def process_pdf_task(self, user_id: int, file_path: str, filename: str):
    """Enhanced Celery task with language support and improved caching"""
    task_id = self.request.id
    
    logger.info(f"Starting PDF processing task for user {user_id} in Celery worker")
    logger.info(f" Task ID: {task_id}")
    logger.info(f" File: {filename}")
    logger.info(f" Path: {file_path}")
    logger.info(f"Process ID: {os.getpid()}")  # Show which process is running
    
    try:
        # Validate file exists before processing
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        # Update task status
        self.update_state(state='PROCESSING', meta={'message': 'Starting PDF processing...'})
        TaskService.update_task_status(task_id, 'processing', 'Starting PDF processing...')
        
        processor = DocumentProcessor()
        
        # Update progress - Loading PDF
        logger.info("Loading and extracting text from PDF...")
        self.update_state(state='PROCESSING', meta={'message': 'Loading and extracting text from PDF...'})
        TaskService.update_task_status(task_id, 'processing', 'Loading and extracting text from PDF...')
        
        # Enhanced PDF processing
        # Extract filename from file_path if not provided
        if not filename:
            filename = os.path.basename(file_path)
        
        page_texts, language = processor.process_pdf(file_path, filename)
        total_chars = sum(len(page['text']) for page in page_texts)
        logger.info(f"PDF text extracted successfully - {total_chars} characters from {len(page_texts)} pages, Language: {language}")
        
        # Update progress - Text splitting
        logger.info(f"Splitting {language} text into chunks...")
        self.update_state(state='PROCESSING', meta={'message': f'Splitting {language} text into chunks...'})
        TaskService.update_task_status(task_id, 'processing', f'Splitting {language} text into chunks...')
        chunks_with_metadata = processor.split_text_with_metadata(page_texts)
        logger.info(f"Text split into {len(chunks_with_metadata)} chunks for {language} processing")
        
        # Update progress - Creating embeddings
        logger.info(f"Creating {language} embeddings...")
        self.update_state(state='PROCESSING', meta={'message': f'Creating {language} embeddings...'})
        TaskService.update_task_status(task_id, 'processing', f'Creating {language} embeddings...')
        vector_store = processor.create_vector_store_with_metadata(chunks_with_metadata, language)
        logger.info(f"Vector store created with {vector_store.index.ntotal} vectors using {language} embeddings")

        vector_store_dir = os.path.join(processor.vector_store_dir, f"user_{user_id}")
        os.makedirs(vector_store_dir, exist_ok=True)
        
        # Update progress - Saving vector store
        logger.info(f"Saving {language} vector store...")
        self.update_state(state='PROCESSING', meta={'message': 'Saving vector store...'})
        TaskService.update_task_status(task_id, 'processing', 'Saving vector store...')
        
        vector_store_path = os.path.join(vector_store_dir, "current_pdf")
        vector_store.save_local(vector_store_path, index_name="index")
        
        if not os.path.exists(os.path.join(vector_store_path, "index.faiss")):
            raise Exception("Vector store files not created properly")
            
        logger.info(f"Vector store saved to: {vector_store_path}")

        # Update progress - Updating database with language info
        logger.info("Finalizing database update with language information...")
        self.update_state(state='PROCESSING', meta={'message': 'Finalizing...'})
        TaskService.update_task_status(task_id, 'processing', 'Finalizing...')

        # Get embedding model name for saving (always English now)
        embedding_model = EmbeddingManager.MODEL

        with get_db_connection() as conn:
            save_vector_store_path(conn, user_id, vector_store_path, language, embedding_model)

        # Mark task as completed
        TaskService.update_task_status(task_id, 'completed', f'{language.title()} PDF processed successfully')

        logger.info(f"{language.title()} PDF processing completed successfully for user {user_id}")
        logger.info(f"Final stats: {vector_store.index.ntotal} vectors, {len(chunks_with_metadata)} chunks, Language: {language}")
        logger.info(f"Embedding model used: {embedding_model}")

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
        
        # Update Celery state with proper format
        self.update_state(
            state='FAILURE',
            meta={
                'message': str(e),
                'error': error_msg,
                'exc_type': type(e).__name__,
                'exc_message': str(e)
            }
        )
        
        # Re-raise the exception with proper Celery format
        raise Exception(error_msg) 

@celery_app.task(bind=True)
def process_admin_pdf_task(self, document_id: int, file_path: str, filename: str):
    """Process PDF for admin global knowledge base using single global vector store"""
    task_id = self.request.id
    
    logger.info(f"Starting admin PDF processing task for document {document_id}")
    logger.info(f" Task ID: {task_id}")
    logger.info(f" File: {filename}")
    logger.info(f" Path: {file_path}")
    
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        # Update task and document status
        self.update_state(state='PROCESSING', meta={'message': 'Starting admin PDF processing...'})
        TaskService.update_task_status(task_id, 'processing', 'Starting admin PDF processing...')
        AdminDocumentService.update_document_processing_status(document_id, 'processing')
        
        processor = DocumentProcessor()
        
        # Extract and process PDF
        logger.info("Loading and extracting text from admin PDF...")
        self.update_state(state='PROCESSING', meta={'message': 'Loading and extracting text...'})
        TaskService.update_task_status(task_id, 'processing', 'Loading and extracting text...')
        
        page_texts, language = processor.process_pdf(file_path, filename)
        total_chars = sum(len(page['text']) for page in page_texts)
        logger.info(f"Admin PDF text extracted - {total_chars} characters from {len(page_texts)} pages, Language: {language}")
        
        # Split text into chunks
        logger.info(f"Splitting {language} text into chunks...")
        self.update_state(state='PROCESSING', meta={'message': f'Splitting {language} text into chunks...'})
        TaskService.update_task_status(task_id, 'processing', f'Splitting {language} text into chunks...')
        chunks_with_metadata = processor.split_text_with_metadata(page_texts)
        logger.info(f"Text split into {len(chunks_with_metadata)} chunks for admin document")
        
        # Add directly to global vector store using the new manager
        logger.info("Adding chunks directly to global vector store...")
        self.update_state(state='PROCESSING', meta={'message': 'Adding to global vector store...'})
        TaskService.update_task_status(task_id, 'processing', 'Adding to global vector store...')
        
        from .app.services.global_vector_store_manager import GlobalVectorStoreManager
        global_manager = GlobalVectorStoreManager()
        
        success = global_manager.add_document_to_global_store(document_id, chunks_with_metadata)
        
        if not success:
            raise Exception("Failed to add document to global vector store")
        
        # Get updated stats
        stats = global_manager.get_global_store_stats()
        logger.info(f"Global vector store updated - Total vectors: {stats['total_vectors']}, Total documents: {stats['total_documents']}")

        # Update database records
        logger.info("Finalizing admin document processing...")
        self.update_state(state='PROCESSING', meta={'message': 'Finalizing admin document...'})
        TaskService.update_task_status(task_id, 'processing', 'Finalizing admin document...')

        embedding_model = EmbeddingManager.MODEL

        # Update admin document record
        AdminDocumentService.update_document_processing_status(
            document_id, 
            'completed', 
            stats['store_path'], 
            language
        )

        # Clear global cache so users get the new document immediately
        clear_global_cache()
        logger.info("Cleared global cache after admin document processing")

        # Mark task as completed
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
        
        # Update task and document status
        try:
            TaskService.update_task_status(task_id, 'failed', str(e))
            AdminDocumentService.update_document_processing_status(document_id, 'failed')
        except Exception as db_error:
            logger.error(f"Failed to update admin task status: {db_error}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'message': str(e),
                'error': error_msg,
                'document_id': document_id,
                'exc_type': type(e).__name__,
                'exc_message': str(e)
            }
        )
        
        raise Exception(error_msg) 