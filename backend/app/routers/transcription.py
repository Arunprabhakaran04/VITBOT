"""
Audio Transcription Router using Groq Whisper-Large-v3
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import os
import tempfile
import requests
from loguru import logger
from dotenv import load_dotenv

from ...oauth2 import get_current_user
from ...schemas import TokenData

load_dotenv()

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

class TranscriptionResponse(BaseModel):
    transcript: str
    language: str = None
    duration: float = None

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Transcribe audio file to text using Groq Whisper-Large-v3
    
    Accepts audio files in formats: mp3, mp4, mpeg, mpga, m4a, wav, webm
    Maximum file size: 25MB
    """
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not found in environment variables")
        raise HTTPException(
            status_code=500,
            detail="Audio transcription service not configured"
        )
    
    allowed_formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
    file_extension = file.filename.split(".")[-1].lower()
    
    if file_extension not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Allowed formats: {', '.join(allowed_formats)}"
        )
    
    try:
        audio_data = await file.read()
        
        if len(audio_data) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Audio file size exceeds 25MB limit"
            )
        
        logger.info(f"Transcribing audio file for user {current_user.id}: {file.filename} ({len(audio_data)} bytes)")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, "rb") as audio_file:
                response = requests.post(
                    GROQ_TRANSCRIPTION_URL,
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}"
                    },
                    files={
                        "file": (file.filename, audio_file, f"audio/{file_extension}")
                    },
                    data={
                        "model": "whisper-large-v3",
                        "response_format": "verbose_json"
                    },
                    timeout=30
                )
            
            if response.status_code != 200:
                logger.error(f"Groq API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Transcription failed: {response.text}"
                )
            
            result = response.json()
            transcript = result.get("text", "").strip()
            language = result.get("language")
            duration = result.get("duration")
            
            if not transcript:
                raise HTTPException(
                    status_code=400,
                    detail="No speech detected in audio"
                )
            
            logger.info(f"Transcription successful for user {current_user.id}: '{transcript[:100]}...' (language: {language})")
            
            return TranscriptionResponse(
                transcript=transcript,
                language=language,
                duration=duration
            )
            
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    except HTTPException:
        raise
    except requests.RequestException as e:
        logger.error(f"Network error during transcription: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Transcription service unavailable"
        )
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to transcribe audio"
        )

@router.get("/transcribe/health")
async def transcription_health():
    """
    Check if transcription service is available
    """
    if not GROQ_API_KEY:
        return {
            "status": "unavailable",
            "message": "GROQ_API_KEY not configured"
        }
    
    return {
        "status": "available",
        "model": "whisper-large-v3",
        "supported_formats": ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"],
        "max_file_size_mb": 25
    }
