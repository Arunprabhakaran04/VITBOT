import os
from fastapi import UploadFile
import shutil
from datetime import datetime

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '../../uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_user_upload_dir(user_id: str) -> str:
    """Get the upload directory for a specific user"""
    return os.path.join(UPLOAD_DIR, f"user_{user_id}")

def save_pdf_file(uploaded_file: UploadFile, user_id: str) -> str:
    user_dir = get_user_upload_dir(user_id)
    os.makedirs(user_dir, exist_ok=True)

    cleanup_user_files(user_dir)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{uploaded_file.filename}"
    file_path = os.path.join(user_dir, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)

    return file_path

def cleanup_user_files(user_dir: str):
    """Clean up all files in a user's directory"""
    try:
        if os.path.exists(user_dir):
            for filename in os.listdir(user_dir):
                file_path = os.path.join(user_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"Removed file: {file_path}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        print(f"Removed directory: {file_path}")
                except Exception as e:
                    print(f"Warning: Could not remove {file_path}: {e}")
            print(f"Cleaned up user directory: {user_dir}")
    except Exception as e:
        print(f"Warning: Could not clean up user files: {e}")