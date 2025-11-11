"""
Enhanced Retrieval Service
Implements Hybrid Search (BM25 + FAISS) and Contextual Chunk Merging
"""
import re
from typing import List, Dict, Any, Optional
from langchain.schema import Document
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from loguru import logger


class ContextualChunkMerger:
    """
    Merges adjacent chunks from the same page/section to provide better context
    Fix 5: Contextual Chunk Merging
    """
    
    def __init__(self, max_merged_size: int = 2500, enable_merging: bool = True):
        """
        Initialize the chunk merger.
        
        Args:
            max_merged_size: Maximum character size for merged chunks
            enable_merging: Toggle to enable/disable merging
        """
        self.max_merged_size = max_merged_size
        self.enable_merging = enable_merging
    
    def merge_adjacent_chunks(self, retrieved_chunks: List[Document]) -> List[Document]:
        """
        Merge adjacent chunks from the same page/section.
        
        Args:
            retrieved_chunks: List of documents retrieved from vector store
            
        Returns:
            List of merged documents with improved context
        """
        if not self.enable_merging or not retrieved_chunks:
            return retrieved_chunks
        
        try:
            # Sort chunks by page number and chunk index for proper ordering
            sorted_chunks = sorted(
                retrieved_chunks,
                key=lambda x: (
                    x.metadata.get('page_number', x.metadata.get('page', 0)),
                    x.metadata.get('chunk_index', 0)
                )
            )
            
            merged = []
            current_group = []
            current_page = None
            current_section = None
            
            for chunk in sorted_chunks:
                page = chunk.metadata.get('page_number', chunk.metadata.get('page'))
                section = self._extract_section_id(chunk)
                
                # Check if this chunk is adjacent to current group
                if self._should_merge_with_group(chunk, current_group, current_page, 
                                                 current_section, page, section):
                    current_group.append(chunk)
                else:
                    # Finalize previous group
                    if current_group:
                        merged_doc = self._merge_chunk_group(current_group)
                        if merged_doc:
                            merged.append(merged_doc)
                    
                    # Start new group
                    current_group = [chunk]
                    current_page = page
                    current_section = section
            
            # Add final group
            if current_group:
                merged_doc = self._merge_chunk_group(current_group)
                if merged_doc:
                    merged.append(merged_doc)
            
            logger.info(f"Merged {len(retrieved_chunks)} chunks into {len(merged)} contextual chunks")
            return merged
            
        except Exception as e:
            logger.error(f"Error in chunk merging: {e}")
            return retrieved_chunks
    
    def _should_merge_with_group(self, chunk: Document, current_group: List[Document],
                                 current_page: Optional[int], current_section: Optional[str],
                                 page: Optional[int], section: Optional[str]) -> bool:
        """Determine if chunk should be merged with current group."""
        if not current_group:
            return False
        
        # Check page match
        if page != current_page:
            return False
        
        # Check section match (if available)
        if section and current_section and section != current_section:
            return False
        
        # Check total size wouldn't exceed limit
        current_size = sum(len(c.page_content) for c in current_group)
        if current_size + len(chunk.page_content) > self.max_merged_size:
            return False
        
        return True
    
    def _extract_section_id(self, chunk: Document) -> Optional[str]:
        """Extract section identifier from chunk metadata or content."""
        # Try to get from metadata
        content_type = chunk.metadata.get('content_type')
        table_type = chunk.metadata.get('table_type')
        
        if content_type:
            return f"{content_type}_{table_type}" if table_type else content_type
        
        # Try to extract from content (look for section numbers like 9.5, 10.2, etc.)
        content = chunk.page_content[:200]  # Check first 200 chars
        section_match = re.search(r'\b(\d+\.\d+(?:\.\d+)?)\s', content)
        if section_match:
            return f"section_{section_match.group(1)}"
        
        return None
    
    def _merge_chunk_group(self, chunks: List[Document]) -> Optional[Document]:
        """Combine multiple chunks into one document."""
        if not chunks:
            return None
        
        if len(chunks) == 1:
            return chunks[0]
        
        # Merge content with appropriate separators
        merged_content_parts = []
        for chunk in chunks:
            content = chunk.page_content.strip()
            if content:
                merged_content_parts.append(content)
        
        merged_content = '\n\n'.join(merged_content_parts)
        
        # Merge metadata
        merged_metadata = chunks[0].metadata.copy()
        merged_metadata['merged_chunks'] = len(chunks)
        merged_metadata['merged_from_indices'] = [
            c.metadata.get('chunk_index', 0) for c in chunks
        ]
        
        # Keep track of all sources
        if len(chunks) > 1:
            merged_metadata['chunk_range'] = f"{chunks[0].metadata.get('chunk_index', 0)}-{chunks[-1].metadata.get('chunk_index', 0)}"
        
        return Document(page_content=merged_content, metadata=merged_metadata)


class HybridSearchRetriever:
    """
    Hybrid retrieval combining FAISS (semantic) and BM25 (keyword) search.
    Fix 1: Hybrid Search (BM25 + FAISS)
    """
    
    def __init__(self, vectorstore: FAISS, documents: List[Document],
                 semantic_weight: float = 0.6, keyword_weight: float = 0.4,
                 enable_hybrid: bool = True):
        """
        Initialize hybrid retriever.
        
        Args:
            vectorstore: FAISS vector store for semantic search
            documents: List of all documents for BM25 indexing
            semantic_weight: Weight for FAISS semantic search (0-1)
            keyword_weight: Weight for BM25 keyword search (0-1)
            enable_hybrid: Toggle to enable/disable hybrid search
        """
        self.vectorstore = vectorstore
        self.documents = documents
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        self.enable_hybrid = enable_hybrid
        self.bm25_retriever = None
        
        if self.enable_hybrid:
            self._initialize_bm25()
    
    def _initialize_bm25(self):
        """Initialize BM25 retriever from documents."""
        try:
            if not self.documents:
                logger.warning("No documents provided for BM25 indexing")
                return
            
            # Create BM25 retriever
            self.bm25_retriever = BM25Retriever.from_documents(self.documents)
            logger.info(f"BM25 retriever initialized with {len(self.documents)} documents")
            
        except Exception as e:
            logger.error(f"Error initializing BM25 retriever: {e}")
            self.bm25_retriever = None
    
    def get_relevant_documents(self, query: str, k: int = 10) -> List[Document]:
        """
        Retrieve documents using hybrid search.
        
        Args:
            query: User query
            k: Number of documents to retrieve
            
        Returns:
            List of retrieved documents
        """
        if not self.enable_hybrid or self.bm25_retriever is None:
            # Fall back to pure FAISS search
            return self.vectorstore.similarity_search(query, k=k)
        
        try:
            # Create ensemble retriever
            faiss_retriever = self.vectorstore.as_retriever(search_kwargs={"k": k})
            self.bm25_retriever.k = k
            
            ensemble_retriever = EnsembleRetriever(
                retrievers=[faiss_retriever, self.bm25_retriever],
                weights=[self.semantic_weight, self.keyword_weight]
            )
            
            # Get hybrid results
            results = ensemble_retriever.get_relevant_documents(query)
            
            logger.info(f"Hybrid search retrieved {len(results)} documents for query: {query[:50]}...")
            return results[:k]  # Ensure we return exactly k documents
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            # Fall back to FAISS only
            return self.vectorstore.similarity_search(query, k=k)


class QueryExpander:
    """
    Expands user queries to improve retrieval coverage.
    Part of Fix 1: Generates semantic variations of the query.
    """
    
    def __init__(self, llm: ChatGroq, enable_expansion: bool = True):
        """
        Initialize query expander.
        
        Args:
            llm: Language model for query expansion
            enable_expansion: Toggle to enable/disable expansion
        """
        self.llm = llm
        self.enable_expansion = enable_expansion
    
    def expand_query(self, query: str, num_variations: int = 3) -> List[str]:
        """
        Generate semantic variations of the query.
        
        Args:
            query: Original user query
            num_variations: Number of variations to generate
            
        Returns:
            List of query variations including original
        """
        if not self.enable_expansion:
            return [query]
        
        try:
            expansion_prompt = f"""Given this question about academic grading/policies: "{query}"

Generate {num_variations} alternative phrasings that capture:
1. Key terms and definitions
2. Numeric/formula keywords (e.g., percentages, grade points, formulas)
3. Related concepts (e.g., requirements, criteria, conditions)

Return ONLY the variations, one per line, without numbering or explanation."""

            response = self.llm.invoke(expansion_prompt)
            variations = [line.strip() for line in response.content.split('\n') if line.strip()]
            
            # Add original query
            all_queries = [query] + variations[:num_variations]
            
            logger.info(f"Expanded query into {len(all_queries)} variations")
            return all_queries
            
        except Exception as e:
            logger.error(f"Error in query expansion: {e}")
            return [query]


class EnhancedRetriever:
    """
    Main enhanced retriever combining all improvements.
    Integrates Fix 1 (Hybrid Search) and Fix 5 (Contextual Merging).
    """
    
    def __init__(self, vectorstore: FAISS, documents: List[Document],
                 llm: Optional[ChatGroq] = None,
                 enable_hybrid: bool = True,
                 enable_merging: bool = True,
                 enable_query_expansion: bool = False,
                 semantic_weight: float = 0.6,
                 keyword_weight: float = 0.4):
        """
        Initialize enhanced retriever with all features.
        
        Args:
            vectorstore: FAISS vector store
            documents: List of all documents
            llm: Language model for query expansion (optional)
            enable_hybrid: Enable hybrid search
            enable_merging: Enable contextual chunk merging
            enable_query_expansion: Enable query expansion (requires llm)
            semantic_weight: Weight for semantic search
            keyword_weight: Weight for keyword search
        """
        self.vectorstore = vectorstore
        self.documents = documents
        self.llm = llm
        
        # Initialize components
        self.hybrid_retriever = HybridSearchRetriever(
            vectorstore=vectorstore,
            documents=documents,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
            enable_hybrid=enable_hybrid
        )
        
        self.chunk_merger = ContextualChunkMerger(
            max_merged_size=2500,
            enable_merging=enable_merging
        )
        
        self.query_expander = None
        if enable_query_expansion and llm:
            self.query_expander = QueryExpander(
                llm=llm,
                enable_expansion=True
            )
        
        logger.info(f"EnhancedRetriever initialized - Hybrid: {enable_hybrid}, "
                   f"Merging: {enable_merging}, Expansion: {enable_query_expansion}")
    
    def get_relevant_documents(self, query: str, k: int = 10) -> List[Document]:
        """
        Retrieve documents with all enhancements.
        
        Args:
            query: User query
            k: Number of documents to retrieve
            
        Returns:
            List of enhanced retrieved documents
        """
        try:
            # Step 1: Query expansion (optional)
            queries = [query]
            if self.query_expander:
                queries = self.query_expander.expand_query(query, num_variations=2)
            
            # Step 2: Hybrid retrieval for each query
            all_docs = []
            for q in queries:
                docs = self.hybrid_retriever.get_relevant_documents(q, k=k)
                all_docs.extend(docs)
            
            # Remove duplicates based on content
            unique_docs = self._deduplicate_documents(all_docs)
            
            # Step 3: Contextual merging
            merged_docs = self.chunk_merger.merge_adjacent_chunks(unique_docs[:k*2])
            
            # Return top k after merging
            final_docs = merged_docs[:k]
            
            logger.info(f"Enhanced retrieval: {len(all_docs)} initial → "
                       f"{len(unique_docs)} unique → {len(merged_docs)} merged → "
                       f"{len(final_docs)} final")
            
            return final_docs
            
        except Exception as e:
            logger.error(f"Error in enhanced retrieval: {e}")
            # Fall back to basic FAISS search
            return self.vectorstore.similarity_search(query, k=k)
    
    def _deduplicate_documents(self, documents: List[Document]) -> List[Document]:
        """Remove duplicate documents based on content similarity."""
        if not documents:
            return []
        
        unique_docs = []
        seen_content = set()
        
        for doc in documents:
            # Create content signature (first 200 chars)
            signature = doc.page_content[:200].strip().lower()
            
            if signature not in seen_content:
                seen_content.add(signature)
                unique_docs.append(doc)
        
        return unique_docs


def create_enhanced_retriever(vectorstore: FAISS, 
                              documents: Optional[List[Document]] = None,
                              llm: Optional[ChatGroq] = None,
                              enable_hybrid: bool = True,
                              enable_merging: bool = True,
                              enable_query_expansion: bool = False) -> EnhancedRetriever:
    """
    Factory function to create an enhanced retriever.
    
    Args:
        vectorstore: FAISS vector store
        documents: List of documents (will be extracted from vectorstore if None)
        llm: Language model for query expansion
        enable_hybrid: Enable hybrid BM25 + FAISS search
        enable_merging: Enable contextual chunk merging
        enable_query_expansion: Enable query expansion
        
    Returns:
        EnhancedRetriever instance
    """
    # Extract documents from vectorstore if not provided
    if documents is None:
        try:
            # Get documents from FAISS index
            documents = []
            if hasattr(vectorstore, 'docstore') and hasattr(vectorstore.docstore, '_dict'):
                documents = list(vectorstore.docstore._dict.values())
            
            if not documents:
                logger.warning("No documents extracted from vectorstore, hybrid search will be disabled")
                enable_hybrid = False
        except Exception as e:
            logger.error(f"Error extracting documents from vectorstore: {e}")
            enable_hybrid = False
            documents = []
    
    return EnhancedRetriever(
        vectorstore=vectorstore,
        documents=documents,
        llm=llm,
        enable_hybrid=enable_hybrid,
        enable_merging=enable_merging,
        enable_query_expansion=enable_query_expansion
    )
