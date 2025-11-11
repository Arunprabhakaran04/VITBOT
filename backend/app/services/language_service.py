import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class LanguageDetector:
    """Enhanced language detector supporting English and Indian languages (Tamil, Hindi, Telugu, etc.)"""
    
    # Supported languages
    SUPPORTED_LANGUAGES = ['english', 'tamil', 'hindi', 'telugu', 'kannada', 'malayalam', 'bengali', 'marathi', 'gujarati', 'punjabi', 'urdu']
    
    def __init__(self):
        self._langdetect_available = False
        self._fasttext_available = False
        
        # Try to initialize language detection libraries
        try:
            import langdetect
            self._langdetect_available = True
            logger.info("langdetect library available for language detection")
        except ImportError:
            logger.warning("langdetect library not available, using fallback detection")
        
        try:
            import fasttext
            self._fasttext_available = True
            logger.info("fasttext library available for language detection")
        except ImportError:
            logger.debug("fasttext library not available")
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the given text
        
        Returns language code: 'english', 'tamil', 'hindi', 'telugu', etc.
        """
        try:
            if not text or len(text.strip()) < 50:
                logger.warning("Text too short for reliable language detection, defaulting to English")
                return 'english'
            
            # Use langdetect if available (most reliable)
            if self._langdetect_available:
                detected = self._detect_with_langdetect(text)
                if detected:
                    logger.info(f"Detected language: {detected}")
                    return detected
            
            # Fallback to character-based detection
            detected = self._detect_by_unicode_ranges(text)
            logger.info(f"Detected language (fallback): {detected}")
            return detected
            
        except Exception as e:
            logger.error(f"Error in language detection: {e}")
            # Default fallback to English
            return 'english'
    
    def _detect_with_langdetect(self, text: str) -> Optional[str]:
        """Detect language using langdetect library"""
        try:
            import langdetect
            
            # Detect language (returns ISO 639-1 code)
            lang_code = langdetect.detect(text)
            
            # Map ISO codes to our language names
            language_map = {
                'en': 'english',
                'ta': 'tamil',
                'hi': 'hindi',
                'te': 'telugu',
                'kn': 'kannada',
                'ml': 'malayalam',
                'bn': 'bengali',
                'mr': 'marathi',
                'gu': 'gujarati',
                'pa': 'punjabi',
                'ur': 'urdu'
            }
            
            detected_lang = language_map.get(lang_code, 'english')
            
            # Get confidence score
            lang_probs = langdetect.detect_langs(text)
            confidence = lang_probs[0].prob if lang_probs else 0.0
            
            logger.info(f"langdetect: {detected_lang} (confidence: {confidence:.2f})")
            
            # If confidence is too low, check with character-based detection
            if confidence < 0.7:
                logger.warning(f"Low confidence ({confidence:.2f}), verifying with character-based detection")
                char_based = self._detect_by_unicode_ranges(text)
                if char_based != detected_lang:
                    logger.info(f"Character-based detection suggests: {char_based}")
                    return char_based
            
            return detected_lang
            
        except Exception as e:
            logger.error(f"langdetect failed: {e}")
            return None
    
    def _detect_by_unicode_ranges(self, text: str) -> str:
        """Detect language based on Unicode character ranges"""
        try:
            # Count characters in different script ranges
            tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))  # Tamil script
            hindi_chars = len(re.findall(r'[\u0900-\u097F]', text))  # Devanagari (Hindi)
            telugu_chars = len(re.findall(r'[\u0C00-\u0C7F]', text))  # Telugu script
            kannada_chars = len(re.findall(r'[\u0C80-\u0CFF]', text))  # Kannada script
            malayalam_chars = len(re.findall(r'[\u0D00-\u0D7F]', text))  # Malayalam script
            bengali_chars = len(re.findall(r'[\u0980-\u09FF]', text))  # Bengali script
            gujarati_chars = len(re.findall(r'[\u0A80-\u0AFF]', text))  # Gujarati script
            punjabi_chars = len(re.findall(r'[\u0A00-\u0A7F]', text))  # Gurmukhi (Punjabi) script
            
            english_chars = len(re.findall(r'[a-zA-Z]', text))
            
            # Remove whitespace for percentage calculation
            non_space_text = re.sub(r'\s+', '', text)
            total_chars = len(non_space_text)
            
            if total_chars == 0:
                return 'english'
            
            # Calculate percentages
            script_percentages = {
                'tamil': (tamil_chars / total_chars) * 100,
                'hindi': (hindi_chars / total_chars) * 100,
                'telugu': (telugu_chars / total_chars) * 100,
                'kannada': (kannada_chars / total_chars) * 100,
                'malayalam': (malayalam_chars / total_chars) * 100,
                'bengali': (bengali_chars / total_chars) * 100,
                'gujarati': (gujarati_chars / total_chars) * 100,
                'punjabi': (punjabi_chars / total_chars) * 100,
                'english': (english_chars / total_chars) * 100
            }
            
            # Find dominant script
            max_script = max(script_percentages.items(), key=lambda x: x[1])
            
            logger.debug(f"Script distribution: {script_percentages}")
            logger.info(f"Dominant script: {max_script[0]} ({max_script[1]:.1f}%)")
            
            # Require at least 20% of text to be in a script to detect it
            if max_script[1] >= 20:
                return max_script[0]
            
            # Default to English if no clear script dominance
            return 'english'
            
        except Exception as e:
            logger.error(f"Character-based detection failed: {e}")
            return 'english'
    
    def get_language_family(self, language: str) -> str:
        """
        Get the language family for model selection
        Returns: 'english' or 'multilingual'
        """
        if language.lower() in ['english', 'en']:
            return 'english'
        else:
            return 'multilingual'
    
    def validate_text_quality(self, text: str) -> bool:
        """
        Check if extracted text has sufficient quality for processing
        """
        if not text or len(text.strip()) < 100:
            return False
        
        # Check if text has readable characters (English or Indian scripts)
        printable_chars = len(re.findall(r'[a-zA-Z0-9\s\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0A80-\u0AFF\u0B00-\u0B7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F]', text))
        total_chars = len(text)
        
        if total_chars > 0:
            quality_ratio = printable_chars / total_chars
            return quality_ratio > 0.5  # At least 50% should be readable characters
        
        return False
    
    def get_text_stats(self, text: str) -> dict:
        """
        Get statistics about the text for debugging
        """
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
        hindi_chars = len(re.findall(r'[\u0900-\u097F]', text))
        telugu_chars = len(re.findall(r'[\u0C00-\u0C7F]', text))
        
        total_chars = len(re.sub(r'\s+', '', text))
        
        return {
            'total_chars': len(text),
            'total_non_space_chars': total_chars,
            'english_chars': english_chars,
            'tamil_chars': tamil_chars,
            'hindi_chars': hindi_chars,
            'telugu_chars': telugu_chars,
            'english_ratio': english_chars / total_chars if total_chars > 0 else 0,
            'tamil_ratio': tamil_chars / total_chars if total_chars > 0 else 0,
            'hindi_ratio': hindi_chars / total_chars if total_chars > 0 else 0,
            'telugu_ratio': telugu_chars / total_chars if total_chars > 0 else 0
        }
