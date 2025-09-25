import os
import pytest

def test_pdf_file_exists():
    file_path = r'D:\FastAPI\social_media_api\backend\uploads\user_17\20250909212431_kv_resume_iter_2 (1).pdf'
    assert os.path.exists(file_path), f"PDF file not found: {file_path}"