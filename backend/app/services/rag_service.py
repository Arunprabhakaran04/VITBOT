import os
import hashlib
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

# Global cache for embeddings model - production-ready singleton pattern
_embeddings_model = None
_embeddings_lock = None

class DocumentProcessor:
    def __init__(self, groq_api_key=None):
        global _embeddings_lock
        if _embeddings_lock is None:
            import threading
            _embeddings_lock = threading.Lock()
            
        self.api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not provided or set in environment")
        os.environ["GROQ_API_KEY"] = self.api_key

        # Initialize services for English document processing
        self.language_detector = LanguageDetector()
        self.pdf_extractor = EnhancedPDFExtractor()
        self.embedding_manager = EmbeddingManager()
        self.text_splitter = TextSplitter()
        
        # Keep legacy embeddings for backward compatibility
        self.embeddings = self._initialize_embeddings()
        self.llm = self._initialize_llm()
        self.vector_store_dir = os.path.join(os.path.dirname(__file__), '../../vector_stores')
        os.makedirs(self.vector_store_dir, exist_ok=True)
        
        logger.info("DocumentProcessor initialized with English support")

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
        """Enhanced PDF processing with metadata tracking"""
        try:
            # Extract text page by page with metadata
            page_texts = self.pdf_extractor.extract_text_with_page_info(pdf_path, filename)
            
            if not page_texts:
                raise ValueError("No text content found in PDF")
            
            # Combine all text for quality validation
            combined_text = ' '.join([page['text'] for page in page_texts])
            
            # Validate text quality
            if not self.language_detector.validate_text_quality(combined_text):
                raise ValueError("Extracted text quality is insufficient for processing")
            
            # Always English now
            language = self.language_detector.detect_language(combined_text)
            logger.info(f"Detected language: {language}")
            
            # Get text statistics for debugging
            stats = self.language_detector.get_text_stats(combined_text)
            logger.info(f"Text stats: {stats['total_chars']} chars, "
                       f"English: {stats['english_ratio']:.1%}")
            
            return page_texts, language
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            raise e

    def split_text_with_metadata(self, page_texts):
        """Text splitting with metadata preservation"""
        try:
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

    def embed_pdf(self, pdf_path, filename):
        """Process PDF with metadata tracking and English embeddings"""
        try:
            # Enhanced PDF processing with metadata
            page_texts, language = self.process_pdf(pdf_path, filename)
            logger.info(f"📄 Processing {language} PDF: {filename}")
            
            # Text splitting with metadata preservation
            chunks_with_metadata = self.split_text_with_metadata(page_texts)
            logger.info(f"✂️ Split into {len(chunks_with_metadata)} chunks for {language} processing")
            
            # Create vector store with metadata
            vector_store = self.create_vector_store_with_metadata(chunks_with_metadata, language)
            
            return vector_store, language
            
        except Exception as e:
            logger.error(f"Error embedding PDF {filename}: {e}")
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