from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List
import logging

logger = logging.getLogger(__name__)

class TextSplitter:
    """
    Text splitter that handles English text
    """
    
    def __init__(self):
        # English separators
        self.english_separators = [
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            ". ",    # Sentence end with space
            "! ",    # Exclamation with space
            "? ",    # Question with space
            "; ",    # Semicolon with space
            ": ",    # Colon with space
            " "      # Space (last resort)
        ]
        
        logger.info("Initialized Text Splitter")
    
    def split_text(self, text: str) -> List[str]:
        """
        Split text using English patterns
        """
        logger.info("Using English text splitting patterns")
        
        try:
            splitter = RecursiveCharacterTextSplitter(
                separators=self.english_separators,
                chunk_size=1000,  # Keep same chunk size
                chunk_overlap=200,  # Keep same overlap
                length_function=len,
                keep_separator=False  # Don't keep separators in chunks
            )
            
            chunks = splitter.split_text(text)
            
            logger.info(f"Split English text into {len(chunks)} chunks")
            
            # Log chunk size statistics
            if chunks:
                chunk_sizes = [len(chunk) for chunk in chunks]
                avg_size = sum(chunk_sizes) / len(chunk_sizes)
                min_size = min(chunk_sizes)
                max_size = max(chunk_sizes)
                
                logger.info(f"Chunk statistics - Avg: {avg_size:.0f}, Min: {min_size}, Max: {max_size}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error splitting English text: {e}")
            raise e
    
    def get_chunk_preview(self, chunks: List[str], max_chunks: int = 3, max_chars: int = 100) -> List[str]:
        """
        Get a preview of the first few chunks for debugging
        """
        previews = []
        for i, chunk in enumerate(chunks[:max_chunks]):
            preview = chunk[:max_chars] + "..." if len(chunk) > max_chars else chunk
            previews.append(f"Chunk {i+1}: {preview}")
        return previews
    
    def split_text_with_metadata(self, page_texts: List[dict]) -> List[dict]:
        """
        Split text from pages into chunks while preserving metadata
        page_texts: List of dicts with 'text' and 'metadata' keys
        Returns: List of dicts with 'text' and 'metadata' keys for each chunk
        """
        logger.info("Using English text splitting patterns with metadata")
        
        try:
            splitter = RecursiveCharacterTextSplitter(
                separators=self.english_separators,
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                keep_separator=False
            )
            
            all_chunks_with_metadata = []
            
            for page_info in page_texts:
                page_text = page_info['text']
                page_metadata = page_info['metadata']
                
                # Split the page text into chunks
                page_chunks = splitter.split_text(page_text)
                
                # Add metadata to each chunk from this page
                for chunk_idx, chunk in enumerate(page_chunks):
                    chunk_metadata = page_metadata.copy()
                    chunk_metadata['chunk_index'] = chunk_idx + 1
                    chunk_metadata['chunks_on_page'] = len(page_chunks)
                    
                    all_chunks_with_metadata.append({
                        'text': chunk,
                        'metadata': chunk_metadata
                    })
            
            logger.info(f"Split English text from {len(page_texts)} pages into {len(all_chunks_with_metadata)} chunks with metadata")
            
            # Log chunk statistics
            if all_chunks_with_metadata:
                chunk_sizes = [len(chunk['text']) for chunk in all_chunks_with_metadata]
                avg_size = sum(chunk_sizes) / len(chunk_sizes)
                min_size = min(chunk_sizes)
                max_size = max(chunk_sizes)
                
                logger.info(f"Chunk statistics - Avg: {avg_size:.0f}, Min: {min_size}, Max: {max_size}")
            
            return all_chunks_with_metadata
            
        except Exception as e:
            logger.error(f"Error splitting English text with metadata: {e}")
            raise e
    
    def validate_chunks(self, chunks: List[str]) -> dict:
        """
        Validate chunk quality and provide statistics
        """
        if not chunks:
            return {'valid': False, 'reason': 'No chunks generated'}
        
        # Check for empty or very short chunks
        valid_chunks = [chunk for chunk in chunks if len(chunk.strip()) > 50]
        
        # Calculate statistics
        total_chunks = len(chunks)
        valid_chunk_count = len(valid_chunks)
        avg_length = sum(len(chunk) for chunk in chunks) / total_chunks if total_chunks > 0 else 0
        
        validation_result = {
            'valid': valid_chunk_count > 0,
            'total_chunks': total_chunks,
            'valid_chunks': valid_chunk_count,
            'invalid_chunks': total_chunks - valid_chunk_count,
            'avg_chunk_length': avg_length,
            'language': 'english'
        }
        
        if valid_chunk_count == 0:
            validation_result['reason'] = 'No chunks with sufficient content (>50 chars)'
        elif valid_chunk_count < total_chunks * 0.8:
            validation_result['warning'] = f'Only {valid_chunk_count}/{total_chunks} chunks have sufficient content'
        
        return validation_result
