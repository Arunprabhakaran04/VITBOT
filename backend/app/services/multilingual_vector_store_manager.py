"""
Multilingual Vector Store Manager
Manages separate FAISS vector stores for English and multilingual documents
with namespace-based organization.
"""

import os
import pickle
from typing import Optional, Dict, List, Any
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from loguru import logger

from .dual_embedding_manager import EmbeddingManager
from .language_service import LanguageDetector


class MultilingualVectorStoreManager:
    """
    Manages separate vector stores for different language namespaces:
    - english_docs: BGE-small-en-v1.5 (384D)
    - multilingual_docs: multilingual-e5-large (1024D)
    """
    
    # Namespace constants
    ENGLISH_NAMESPACE = "english_docs"
    MULTILINGUAL_NAMESPACE = "multilingual_docs"
    
    def __init__(self, base_dir: str = None):
        """
        Initialize the multilingual vector store manager
        
        Args:
            base_dir: Base directory for storing vector stores
        """
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), '../../vector_stores')
        
        self.base_dir = base_dir
        self.language_detector = LanguageDetector()
        self.embedding_manager = EmbeddingManager()
        
        # Create namespace directories
        self.english_dir = os.path.join(base_dir, self.ENGLISH_NAMESPACE)
        self.multilingual_dir = os.path.join(base_dir, self.MULTILINGUAL_NAMESPACE)
        
        os.makedirs(self.english_dir, exist_ok=True)
        os.makedirs(self.multilingual_dir, exist_ok=True)
        
        logger.info(f"Initialized MultilingualVectorStoreManager with base: {base_dir}")
        logger.info(f"  English namespace: {self.english_dir}")
        logger.info(f"  Multilingual namespace: {self.multilingual_dir}")
    
    def get_namespace_for_language(self, language: str) -> str:
        """
        Determine the namespace based on detected language
        
        Args:
            language: Detected language (e.g., 'english', 'tamil', 'hindi')
        
        Returns:
            Namespace string
        """
        if language.lower() in ['english', 'en']:
            return self.ENGLISH_NAMESPACE
        else:
            return self.MULTILINGUAL_NAMESPACE
    
    def get_namespace_dir(self, namespace: str) -> str:
        """Get the directory path for a namespace"""
        if namespace == self.ENGLISH_NAMESPACE:
            return self.english_dir
        elif namespace == self.MULTILINGUAL_NAMESPACE:
            return self.multilingual_dir
        else:
            raise ValueError(f"Unknown namespace: {namespace}")
    
    def get_embeddings_for_namespace(self, namespace: str) -> HuggingFaceEmbeddings:
        """
        Get the appropriate embedding model for a namespace
        
        Args:
            namespace: Namespace identifier
        
        Returns:
            HuggingFaceEmbeddings model
        """
        if namespace == self.ENGLISH_NAMESPACE:
            return self.embedding_manager.get_embeddings('english')
        elif namespace == self.MULTILINGUAL_NAMESPACE:
            return self.embedding_manager.get_embeddings('multilingual')
        else:
            raise ValueError(f"Unknown namespace: {namespace}")
    
    def create_vector_store(
        self, 
        texts: List[str], 
        metadatas: List[Dict[str, Any]], 
        language: str
    ) -> tuple[FAISS, str]:
        """
        Create a vector store for documents in the appropriate namespace
        
        Args:
            texts: List of text chunks
            metadatas: List of metadata dicts for each chunk
            language: Detected language of the documents
        
        Returns:
            Tuple of (FAISS vectorstore, namespace)
        """
        try:
            # Determine namespace
            namespace = self.get_namespace_for_language(language)
            
            # Get appropriate embeddings
            embeddings = self.get_embeddings_for_namespace(namespace)
            
            # Create vector store
            vector_store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
            
            logger.info(f"Created vector store in namespace '{namespace}' with {vector_store.index.ntotal} vectors")
            logger.info(f"  Language: {language}")
            logger.info(f"  Model: {EmbeddingManager.ENGLISH_MODEL if namespace == self.ENGLISH_NAMESPACE else EmbeddingManager.MULTILINGUAL_MODEL}")
            
            return vector_store, namespace
            
        except Exception as e:
            logger.error(f"Error creating vector store for language '{language}': {e}")
            raise
    
    def save_vector_store(
        self, 
        vector_store: FAISS, 
        namespace: str, 
        store_name: str
    ) -> str:
        """
        Save a vector store to the appropriate namespace directory
        
        Args:
            vector_store: FAISS vector store to save
            namespace: Namespace identifier
            store_name: Name for this store (e.g., 'user_123', 'global_knowledge_base')
        
        Returns:
            Path where the vector store was saved
        """
        try:
            namespace_dir = self.get_namespace_dir(namespace)
            store_path = os.path.join(namespace_dir, store_name)
            
            # Create directory if it doesn't exist
            os.makedirs(store_path, exist_ok=True)
            
            # Save vector store
            vector_store.save_local(store_path, index_name="index")
            
            logger.info(f"Saved vector store to '{store_path}' (namespace: {namespace})")
            logger.info(f"  Vectors: {vector_store.index.ntotal}")
            
            return store_path
            
        except Exception as e:
            logger.error(f"Error saving vector store to namespace '{namespace}': {e}")
            raise
    
    def load_vector_store(
        self, 
        namespace: str, 
        store_name: str
    ) -> Optional[FAISS]:
        """
        Load a vector store from a namespace
        
        Args:
            namespace: Namespace identifier
            store_name: Name of the store to load
        
        Returns:
            FAISS vector store or None if not found
        """
        try:
            namespace_dir = self.get_namespace_dir(namespace)
            store_path = os.path.join(namespace_dir, store_name)
            
            # Check if store exists
            index_file = os.path.join(store_path, "index.faiss")
            pkl_file = os.path.join(store_path, "index.pkl")
            
            if not (os.path.exists(index_file) and os.path.exists(pkl_file)):
                logger.debug(f"Vector store not found at '{store_path}'")
                return None
            
            # Get appropriate embeddings for namespace
            embeddings = self.get_embeddings_for_namespace(namespace)
            
            # Load vector store
            vector_store = FAISS.load_local(
                store_path,
                embeddings,
                index_name="index",
                allow_dangerous_deserialization=True
            )
            
            logger.info(f"Loaded vector store from '{store_path}' (namespace: {namespace})")
            logger.info(f"  Vectors: {vector_store.index.ntotal}")
            
            return vector_store
            
        except Exception as e:
            logger.error(f"Error loading vector store from namespace '{namespace}': {e}")
            return None
    
    def merge_vector_stores(
        self, 
        primary_store: FAISS, 
        secondary_store: FAISS,
        primary_namespace: str,
        secondary_namespace: str
    ) -> Optional[FAISS]:
        """
        Merge two vector stores from the same namespace
        
        Note: Can only merge stores from the same namespace (same embedding dimensions)
        
        Args:
            primary_store: Primary vector store
            secondary_store: Secondary vector store to merge
            primary_namespace: Namespace of primary store
            secondary_namespace: Namespace of secondary store
        
        Returns:
            Merged vector store or None if namespaces don't match
        """
        try:
            if primary_namespace != secondary_namespace:
                logger.error(f"Cannot merge stores from different namespaces: {primary_namespace} vs {secondary_namespace}")
                logger.error("Different namespaces use different embedding dimensions and are incompatible")
                return None
            
            # Merge stores
            primary_store.merge_from(secondary_store)
            
            logger.info(f"Merged vector stores in namespace '{primary_namespace}'")
            logger.info(f"  Total vectors after merge: {primary_store.index.ntotal}")
            
            return primary_store
            
        except Exception as e:
            logger.error(f"Error merging vector stores: {e}")
            return None
    
    def get_namespace_stats(self, namespace: str) -> Dict[str, Any]:
        """
        Get statistics for a namespace
        
        Args:
            namespace: Namespace identifier
        
        Returns:
            Dictionary with namespace statistics
        """
        try:
            namespace_dir = self.get_namespace_dir(namespace)
            
            # Count stores in namespace
            store_count = 0
            if os.path.exists(namespace_dir):
                store_count = len([
                    d for d in os.listdir(namespace_dir)
                    if os.path.isdir(os.path.join(namespace_dir, d))
                ])
            
            model_name = (
                EmbeddingManager.ENGLISH_MODEL if namespace == self.ENGLISH_NAMESPACE
                else EmbeddingManager.MULTILINGUAL_MODEL
            )
            dimensions = (
                EmbeddingManager.ENGLISH_DIMENSIONS if namespace == self.ENGLISH_NAMESPACE
                else EmbeddingManager.MULTILINGUAL_DIMENSIONS
            )
            
            return {
                'namespace': namespace,
                'directory': namespace_dir,
                'store_count': store_count,
                'model': model_name,
                'dimensions': dimensions,
                'exists': os.path.exists(namespace_dir)
            }
            
        except Exception as e:
            logger.error(f"Error getting stats for namespace '{namespace}': {e}")
            return {'error': str(e)}
    
    def get_all_namespaces_stats(self) -> Dict[str, Any]:
        """Get statistics for all namespaces"""
        return {
            'english': self.get_namespace_stats(self.ENGLISH_NAMESPACE),
            'multilingual': self.get_namespace_stats(self.MULTILINGUAL_NAMESPACE),
            'base_directory': self.base_dir
        }
    
    def detect_and_route(self, text: str) -> tuple[str, str]:
        """
        Detect language and determine routing
        
        Args:
            text: Text to analyze
        
        Returns:
            Tuple of (language, namespace)
        """
        language = self.language_detector.detect_language(text)
        namespace = self.get_namespace_for_language(language)
        
        logger.info(f"Language detection: '{language}' -> Namespace: '{namespace}'")
        
        return language, namespace
