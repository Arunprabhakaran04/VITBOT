import re
import logging

logger = logging.getLogger(__name__)

class LanguageDetector:
    """Simple text validator for English PDFs"""
    
    def detect_language(self, text: str) -> str:
        """
        Always returns 'english' since we only support English now
        """
        try:
            logger.info("Detected English document")
            return 'english'
            
        except Exception as e:
            logger.error(f"Error in language detection: {e}")
            # Default fallback to English
            return 'english'
    
    def validate_text_quality(self, text: str) -> bool:
        """
        Check if extracted text has sufficient quality for processing
        """
        if not text or len(text.strip()) < 100:
            return False
        
        # Check if text is mostly readable English characters
        printable_chars = len(re.findall(r'[a-zA-Z0-9\s]', text))
        total_chars = len(text)
        
        if total_chars > 0:
            quality_ratio = printable_chars / total_chars
            return quality_ratio > 0.7  # At least 70% should be readable characters
        
        return False
    
    def get_text_stats(self, text: str) -> dict:
        """
        Get statistics about the text for debugging
        """
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_chars = len(re.sub(r'\s+', '', text))
        
        return {
            'total_chars': len(text),
            'total_non_space_chars': total_chars,
            'english_chars': english_chars,
            'english_ratio': english_chars / total_chars if total_chars > 0 else 0
        }
