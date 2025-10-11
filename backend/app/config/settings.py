"""
Configuration settings for the background processing system
"""
import os
from typing import Optional

class BackgroundProcessingSettings:
    """Settings for background PDF processing"""
    
    # Worker configuration
    MAX_BACKGROUND_WORKERS: int = int(os.getenv("MAX_BACKGROUND_WORKERS", "2"))
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    MAX_QUEUE_SIZE: int = int(os.getenv("MAX_QUEUE_SIZE", "100"))
    
    # File storage settings
    TEMP_FILE_DIR: str = os.getenv("TEMP_FILE_DIR", os.path.join(os.getcwd(), "temp"))
    
    # Processing settings
    PDF_PROCESSING_TIMEOUT: int = int(os.getenv("PDF_PROCESSING_TIMEOUT", "300"))  # 5 minutes
    
    # Task cleanup settings
    TASK_CLEANUP_DAYS: int = int(os.getenv("TASK_CLEANUP_DAYS", "7"))
    
    @classmethod
    def get_max_file_size_bytes(cls) -> int:
        """Get max file size in bytes"""
        return cls.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @classmethod
    def ensure_temp_dir(cls) -> None:
        """Ensure temp directory exists"""
        os.makedirs(cls.TEMP_FILE_DIR, exist_ok=True)

# Global settings instance
settings = BackgroundProcessingSettings()