import os
import hashlib
from typing import List, Dict, Any
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from loguru import logger

# Import services for English document processing
from .language_service import LanguageDetector
from .enhanced_pdf_extractor import EnhancedPDFExtractor
from .dual_embedding_manager import EmbeddingManager
from .language_aware_text_splitter import TextSplitter
from .enhanced_pdf_chunker import EnhancedPDFChunker

# Global cache for embeddings model - production-ready singleton pattern
_embeddings_model = None
_embeddings_lock = None

class DocumentProcessor:
    def __init__(self, groq_api_key=None):
        global _embeddings_lock
        if _embeddings_lock is None:
            import threading
            _embeddings_lock = threading.Lock()
        
        # Load from .env file if not provided
        from dotenv import load_dotenv
        load_dotenv()
        
        self.api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not provided or set in environment variables. Please check your .env file.")
        os.environ["GROQ_API_KEY"] = self.api_key

        # Initialize services for English document processing
        self.language_detector = LanguageDetector()
        self.pdf_extractor = EnhancedPDFExtractor()
        self.embedding_manager = EmbeddingManager()
        self.text_splitter = TextSplitter()
        self.enhanced_pdf_chunker = EnhancedPDFChunker()
        
        # Keep legacy embeddings for backward compatibility
        self.embeddings = self._initialize_embeddings()
        self.llm = self._initialize_llm()
        self.vector_store_dir = os.path.join(os.path.dirname(__file__), '../../vector_stores')
        os.makedirs(self.vector_store_dir, exist_ok=True)
        
        logger.info("DocumentProcessor initialized with enhanced PDF chunking support")

    def _initialize_embeddings(self):
        """Thread-safe embeddings model initialization"""
        global _embeddings_model, _embeddings_lock
        
        if _embeddings_model is None:
            with _embeddings_lock:
                # Double-check pattern for thread safety
                if _embeddings_model is None:
                    logger.info("Initializing embeddings model - this may take a few minutes...")
                    logger.info("Downloading/loading BAAI/bge-small-en-v1.5 model...")
                    
                    try:
                        _embeddings_model = HuggingFaceEmbeddings(
                            model_name="BAAI/bge-small-en-v1.5",
                            model_kwargs={"device": "cpu"},
                            encode_kwargs={"normalize_embeddings": True}
                        )
                        logger.success("Embeddings model loaded successfully!")
                    except Exception as e:
                        logger.error(f"Failed to initialize embeddings model: {e}")
                        raise
        else:
            logger.debug("Using cached embeddings model - fast loading!")
        return _embeddings_model
    
    @property  
    def embeddings_model(self):
        """Property to get embeddings model (for startup initialization)"""
        return self._initialize_embeddings()

    def _initialize_llm(self):
        return ChatGroq(
            model_name="llama-3.3-70b-versatile", 
            temperature=0.1
        )

    def get_document_hash(self, file_path):
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def process_pdf(self, pdf_path, filename):
        """Enhanced PDF processing with metadata tracking - now uses enhanced chunker by default"""
        try:
            # Use enhanced chunker for comprehensive text and table extraction
            enhanced_chunks, language = self.process_pdf_enhanced(pdf_path, filename)
            
            # Convert enhanced chunks to page_texts format for backward compatibility
            page_texts = []
            current_page = None
            page_text = []
            
            for chunk in enhanced_chunks:
                page_num = chunk['metadata'].get('page_number')
                if current_page != page_num:
                    # Save previous page if exists
                    if current_page is not None and page_text:
                        page_texts.append({
                            'text': '\n'.join(page_text),
                            'metadata': {
                                'source': filename,
                                'page': current_page,
                                'total_pages': max(c['metadata'].get('page_number', 1) for c in enhanced_chunks)
                            }
                        })
                    # Start new page
                    current_page = page_num
                    page_text = [chunk['content']]
                else:
                    page_text.append(chunk['content'])
            
            # Add final page
            if current_page is not None and page_text:
                page_texts.append({
                    'text': '\n'.join(page_text),
                    'metadata': {
                        'source': filename,
                        'page': current_page,
                        'total_pages': max(c['metadata'].get('page_number', 1) for c in enhanced_chunks)
                    }
                })
            
            logger.info(f"Enhanced processing converted to {len(page_texts)} pages, Language: {language}")
            return page_texts, language
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            raise e

    def process_pdf_enhanced(self, pdf_path, filename):
        """Enhanced PDF processing with text and table extraction"""
        try:
            # Use enhanced chunker for better text and table extraction
            enhanced_chunks = self.enhanced_pdf_chunker.process_pdf_with_enhanced_chunking(pdf_path, filename)
            
            if not enhanced_chunks:
                raise ValueError("No content found in PDF")
            
            # Validate content quality
            combined_text = ' '.join([chunk['content'] for chunk in enhanced_chunks])
            if not self.language_detector.validate_text_quality(combined_text):
                raise ValueError("Extracted content quality is insufficient for processing")
            
            # Always English now
            language = self.language_detector.detect_language(combined_text)
            logger.info(f"Detected language: {language}")
            
            # Get processing statistics
            stats = self.enhanced_pdf_chunker.get_processing_summary(enhanced_chunks)
            logger.info(f"Enhanced processing stats: {stats['total_chunks']} chunks "
                       f"({stats['text_chunks']} text, {stats['table_chunks']} table), "
                       f"{stats['total_characters']} chars from {stats['pages_processed']} pages")
            
            return enhanced_chunks, language
            
        except Exception as e:
            logger.error(f"Error processing PDF with enhanced chunker {pdf_path}: {e}")
            raise e

    def process_pdf_with_enhanced_chunking(self, pdf_path: str, filename: str) -> List[Dict[str, Any]]:
        """Process PDF using enhanced chunking capabilities as the main method."""
        try:
            # Initialize and use enhanced chunker
            enhanced_chunks = self.enhanced_pdf_chunker.process_pdf_with_enhanced_chunking(pdf_path, filename)
            
            if not enhanced_chunks:
                raise ValueError("No content could be extracted from the PDF")
            
            # Convert to format expected by vector store
            processed_chunks = []
            for chunk in enhanced_chunks:
                # Add filename to metadata for citations
                chunk['metadata']['filename'] = filename
                chunk['metadata']['source'] = pdf_path
                
                processed_chunks.append({
                    'text': chunk['content'],
                    'metadata': chunk['metadata']
                })
            
            logger.info(f"Enhanced processing completed: {len(processed_chunks)} chunks "
                       f"({sum(1 for c in enhanced_chunks if c['chunk_type'] == 'text')} text, "
                       f"{sum(1 for c in enhanced_chunks if c['chunk_type'] == 'table')} table)")
            return processed_chunks
            
        except Exception as e:
            logger.error(f"Enhanced PDF processing failed for {filename}: {e}")
            raise e

    def split_text_with_metadata(self, page_texts):
        """Text splitting with metadata preservation - enhanced chunker provides better chunks directly"""
        try:
            # Check if we already have enhanced chunks (from new processing flow)
            if isinstance(page_texts, list) and len(page_texts) > 0 and 'content' in page_texts[0]:
                # Already enhanced chunks, convert to expected format
                chunks_with_metadata = self.process_enhanced_chunks_with_metadata(page_texts)
            else:
                # Legacy page_texts format, use traditional splitting
                chunks_with_metadata = self.text_splitter.split_text_with_metadata(page_texts)
            
            # Validate chunks
            chunk_texts = [chunk['text'] for chunk in chunks_with_metadata]
            validation = self.text_splitter.validate_chunks(chunk_texts)
            if not validation['valid']:
                raise ValueError(f"Text splitting validation failed: {validation.get('reason', 'Unknown error')}")
            
            if 'warning' in validation:
                logger.warning(f"Text splitting warning: {validation['warning']}")
            
            return chunks_with_metadata
            
        except Exception as e:
            logger.error(f"Error splitting text with metadata: {e}")
            raise e
    
    def process_enhanced_chunks_with_metadata(self, enhanced_chunks):
        """Process enhanced chunks for vector store creation"""
        try:
            # Convert enhanced chunks to format expected by vector store
            chunks_with_metadata = self.text_splitter.split_enhanced_chunks_with_metadata(enhanced_chunks)
            
            # Validate chunks
            chunk_texts = [chunk['text'] for chunk in chunks_with_metadata]
            validation = self.text_splitter.validate_chunks(chunk_texts)
            if not validation['valid']:
                raise ValueError(f"Enhanced chunk validation failed: {validation.get('reason', 'Unknown error')}")
            
            if 'warning' in validation:
                logger.warning(f"Enhanced chunk warning: {validation['warning']}")
            
            return chunks_with_metadata
            
        except Exception as e:
            logger.error(f"Error processing enhanced chunks with metadata: {e}")
            raise e

    def embed_pdf(self, pdf_path, filename):
        """Process PDF with enhanced chunking and English embeddings - UPDATED TO USE ENHANCED"""
        try:
            # Use enhanced PDF processing directly
            vector_store, language = self.create_embeddings_from_pdf(pdf_path, filename)
            logger.info(f"📄 Enhanced PDF processing completed for {filename}: {vector_store.index.ntotal} vectors")
            
            return vector_store, language
            
        except Exception as e:
            logger.error(f"Error embedding PDF {filename}: {e}")
            raise e
    
    def embed_pdf_enhanced(self, pdf_path, filename):
        """Process PDF with enhanced chunking (text + tables) and English embeddings - MAIN METHOD"""
        try:
            # Enhanced PDF processing with text and table extraction
            enhanced_chunks, language = self.process_pdf_enhanced(pdf_path, filename)
            logger.info(f"📄 Processing {language} PDF with enhanced chunking: {filename}")
            
            # Process enhanced chunks for vector store
            chunks_with_metadata = self.process_enhanced_chunks_with_metadata(enhanced_chunks)
            logger.info(f"✂️ Processed {len(chunks_with_metadata)} enhanced chunks for {language} processing")
            
            # Create vector store with metadata
            vector_store = self.create_vector_store_with_metadata(chunks_with_metadata, language)
            
            return vector_store, language
            
        except Exception as e:
            logger.error(f"Error embedding PDF with enhanced chunking {filename}: {e}")
            raise e
    
    def create_embeddings_from_pdf(self, pdf_path: str, filename: str):
        """Create embeddings from PDF using enhanced processing - NEW MAIN ENTRY POINT"""
        try:
            # Use enhanced processing for comprehensive text and table extraction
            chunks_with_metadata = self.process_pdf_with_enhanced_chunking(pdf_path, filename)
            
            if not chunks_with_metadata:
                raise ValueError("No content could be extracted from the PDF")
            
            # Create vector store with enhanced chunks using existing method
            embeddings = EmbeddingManager.get_embeddings_static()
            texts = [chunk['text'] for chunk in chunks_with_metadata]
            metadatas = [chunk['metadata'] for chunk in chunks_with_metadata]
            
            # Create vector store with metadata
            vector_store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
            
            logger.info(f"Enhanced embeddings created successfully for {filename}: {vector_store.index.ntotal} vectors")
            return vector_store, 'english'
            
        except Exception as e:
            logger.error(f"Error creating enhanced embeddings for {filename}: {e}")
            raise e

    def create_vector_store_with_metadata(self, chunks_with_metadata, language='english'):
        """Create vector store with English embeddings and metadata"""
        try:
            # Get English embeddings model
            embeddings = EmbeddingManager.get_embeddings_static()
            
            # Extract texts and metadatas for FAISS
            texts = [chunk['text'] for chunk in chunks_with_metadata]
            metadatas = [chunk['metadata'] for chunk in chunks_with_metadata]
            
            # Create vector store with metadata
            vector_store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
            
            logger.info(f"Created {language} vector store with {vector_store.index.ntotal} vectors and metadata")
            return vector_store
            
        except Exception as e:
            logger.error(f"Error creating {language} vector store with metadata: {e}")
            raise e

    # Legacy method for backward compatibility
    def process_pdf_legacy(self, pdf_path):
        """Legacy PDF processing method using PyPDF2 (for backward compatibility)"""
        reader = PdfReader(pdf_path)
        raw_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                raw_text += text
        return raw_text