from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from ...oauth2 import get_current_user
from ..utils.file_utils import save_pdf_file
from ..services.rag_service import DocumentProcessor
from ..services.language_service import LanguageDetector
from ..services.enhanced_pdf_extractor import EnhancedPDFExtractor
from ...database_connection import get_db_connection
from ...vector_store_db import save_vector_store_path
from ..services.rag_handler import clear_user_cache
from loguru import logger
import os
import shutil

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Test models
class TextLanguageRequest(BaseModel):
    text: str

class LanguageDetectionResponse(BaseModel):
    detected_language: str
    text_stats: dict
    is_valid_quality: bool

@router.post("/upload_pdf", status_code=201)
async def upload_pdf(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    user_data = get_current_user(token)
    user_id = user_data.id

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    try:
        cleanup_existing_vectorstore(user_id)
        
        file_path = save_pdf_file(file, user_id)
        logger.info(f"PDF saved to: {file_path}")

        processor = DocumentProcessor()
        vector_store, language = processor.embed_pdf(file_path, file.filename)
        logger.success(f"🔢 Vector store created with {vector_store.index.ntotal} vectors for {language} document")

        vector_store_dir = os.path.join(processor.vector_store_dir, f"user_{user_id}")
        os.makedirs(vector_store_dir, exist_ok=True)
        
        vector_store_path = os.path.join(vector_store_dir, "current_pdf")
        vector_store.save_local(vector_store_path, index_name="index")
        
        if not os.path.exists(os.path.join(vector_store_path, "index.faiss")):
            raise Exception("Vector store files not created properly")
            
        logger.success(f"💾 Vector store saved to: {vector_store_path}")

        with get_db_connection() as conn:
            save_vector_store_path(conn, user_id, vector_store_path, language)

        return {"message": "PDF uploaded and embedded successfully."}

    except Exception as e:
        logger.error(f"❌ Error in upload_pdf: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def cleanup_existing_vectorstore(user_id: int):
    try:
        processor = DocumentProcessor()
        user_vector_dir = os.path.join(processor.vector_store_dir, f"user_{user_id}")
        if os.path.exists(user_vector_dir):
            shutil.rmtree(user_vector_dir)
            logger.info(f"🗑️ Cleaned up existing vector store for user {user_id}")
    except Exception as e:
        logger.warning(f"⚠️ Could not clean up existing vector store: {e}")


# Test endpoints for document processing
@router.post("/test/detect_language", response_model=LanguageDetectionResponse)
async def test_language_detection(request: TextLanguageRequest, token: str = Depends(oauth2_scheme)):
    """Test endpoint to detect language of provided text (always returns English now)"""
    try:
        get_current_user(token)  # Verify user is authenticated
        
        detector = LanguageDetector()
        
        # Always returns English now
        language = detector.detect_language(request.text)
        
        # Get text statistics
        stats = detector.get_text_stats(request.text)
        
        # Check text quality
        is_valid = detector.validate_text_quality(request.text)
        
        logger.info(f"Language detection test: {language} (Quality: {is_valid})")
        
        return LanguageDetectionResponse(
            detected_language=language,
            text_stats=stats,
            is_valid_quality=is_valid
        )
        
    except Exception as e:
        logger.error(f"Error in language detection test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/extract_pdf_text")
async def test_pdf_text_extraction(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    """Test endpoint to extract and analyze text from PDF"""
    try:
        get_current_user(token)  # Verify user is authenticated
        
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Save temporary file
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        try:
            # Extract text and detect language
            extractor = EnhancedPDFExtractor()
            detector = LanguageDetector()
            
            # Extract text
            raw_text = extractor.extract_text(temp_path)
            
            # Always English now
            language = detector.detect_language(raw_text)
            
            # Get statistics
            stats = detector.get_text_stats(raw_text)
            
            # Validate quality
            is_valid = detector.validate_text_quality(raw_text)
            
            # Get text preview
            preview = extractor.get_text_preview(raw_text, 300)
            
            result = {
                "filename": file.filename,
                "detected_language": language,
                "text_length": len(raw_text),
                "text_stats": stats,
                "is_valid_quality": is_valid,
                "text_preview": preview
            }
            
            logger.info(f"PDF text extraction test: {file.filename} -> {language}")
            return result
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        logger.error(f"Error in PDF text extraction test: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # Clear the in-memory cache for this user
    clear_user_cache(user_id)


@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    user_data = get_current_user(token)
    cleanup_existing_vectorstore(user_data.id)
    return {"message": "Logged out successfully"}