import os
import pytest
from your_module import process_pdf_task  # Replace with the actual import

def test_process_pdf_task_file_not_found():
    file_path = "D:\\FastAPI\\social_media_api\\backend\\uploads\\user_17\\20250909212431_kv_resume_iter_2 (1).pdf"
    with pytest.raises(FileNotFoundError) as excinfo:
        process_pdf_task(file_path)
    assert str(excinfo.value) == f"PDF file not found: {file_path}"