#!/usr/bin/env python3
"""
Faster-Whisper STT Server
Real-time speech-to-text with WebSocket streaming support.
Replaces cloud Deepgram with local inference.
"""

import asyncio
import io
import json
import logging
import os
import tempfile
import wave
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
from pydantic import BaseModel
from pydantic_settings import BaseSettings

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Server configuration"""
    model_size: str = "large-v3"  # Options: tiny, base, small, medium, large-v2, large-v3
    device: str = "auto"  # auto, cuda, cpu
    compute_type: str = "auto"  # auto, float16, int8, int8_float16
    host: str = "0.0.0.0"
    port: int = 8001
    
    class Config:
        env_prefix = "STT_"


settings = Settings()

# Global model instance
whisper_model: Optional[WhisperModel] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup"""
    global whisper_model
    
    logger.info(f"Loading Whisper model: {settings.model_size}")
    logger.info(f"Device: {settings.device}, Compute: {settings.compute_type}")
    
    whisper_model = WhisperModel(
        settings.model_size,
        device=settings.device,
        compute_type=settings.compute_type
    )
    
    logger.info("✓ Model loaded successfully")
    yield
    
    # Cleanup
    whisper_model = None
    logger.info("Model unloaded")


app = FastAPI(
    title="Faster-Whisper STT Server",
    description="Local speech-to-text API for Eburon Orbit",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float
    segments: list


class HealthResponse(BaseModel):
    status: str
    model: str
    device: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if whisper_model else "loading",
        model=settings.model_size,
        device=settings.device
    )


@app.get("/languages")
async def list_languages():
    """List supported languages"""
    # Whisper large-v3 supported languages
    languages = {
        "en": "English", "zh": "Chinese", "de": "German", "es": "Spanish",
        "ru": "Russian", "ko": "Korean", "fr": "French", "ja": "Japanese",
        "pt": "Portuguese", "tr": "Turkish", "pl": "Polish", "ca": "Catalan",
        "nl": "Dutch", "ar": "Arabic", "sv": "Swedish", "it": "Italian",
        "id": "Indonesian", "hi": "Hindi", "fi": "Finnish", "vi": "Vietnamese",
        "he": "Hebrew", "uk": "Ukrainian", "el": "Greek", "ms": "Malay",
        "cs": "Czech", "ro": "Romanian", "da": "Danish", "hu": "Hungarian",
        "ta": "Tamil", "no": "Norwegian", "th": "Thai", "ur": "Urdu",
        "hr": "Croatian", "bg": "Bulgarian", "lt": "Lithuanian", "la": "Latin",
        "mi": "Maori", "ml": "Malayalam", "cy": "Welsh", "sk": "Slovak",
        "te": "Telugu", "fa": "Persian", "lv": "Latvian", "bn": "Bengali",
        "sr": "Serbian", "az": "Azerbaijani", "sl": "Slovenian", "kn": "Kannada",
        "et": "Estonian", "mk": "Macedonian", "br": "Breton", "eu": "Basque",
        "is": "Icelandic", "hy": "Armenian", "ne": "Nepali", "mn": "Mongolian",
        "bs": "Bosnian", "kk": "Kazakh", "sq": "Albanian", "sw": "Swahili",
        "gl": "Galician", "mr": "Marathi", "pa": "Punjabi", "si": "Sinhala",
        "km": "Khmer", "sn": "Shona", "yo": "Yoruba", "so": "Somali",
        "af": "Afrikaans", "oc": "Occitan", "ka": "Georgian", "be": "Belarusian",
        "tg": "Tajik", "sd": "Sindhi", "gu": "Gujarati", "am": "Amharic",
        "yi": "Yiddish", "lo": "Lao", "uz": "Uzbek", "fo": "Faroese",
        "ht": "Haitian Creole", "ps": "Pashto", "tk": "Turkmen", "nn": "Nynorsk",
        "mt": "Maltese", "sa": "Sanskrit", "lb": "Luxembourgish", "my": "Myanmar",
        "bo": "Tibetan", "tl": "Tagalog", "mg": "Malagasy", "as": "Assamese",
        "tt": "Tatar", "haw": "Hawaiian", "ln": "Lingala", "ha": "Hausa",
        "ba": "Bashkir", "jw": "Javanese", "su": "Sundanese"
    }
    return {"languages": languages, "count": len(languages)}


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """
    Transcribe audio file.
    Supports: wav, mp3, flac, ogg, webm
    """
    if not whisper_model:
        return JSONResponse(status_code=503, content={"error": "Model not loaded"})
    
    # Read audio file
    audio_bytes = await audio.read()
    
    # Save to temp file (faster-whisper needs file path)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    
    try:
        # Transcribe
        segments, info = whisper_model.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        # Collect results
        segment_list = []
        full_text = []
        
        for segment in segments:
            segment_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "confidence": segment.avg_logprob
            })
            full_text.append(segment.text.strip())
        
        return TranscriptionResponse(
            text=" ".join(full_text),
            language=info.language,
            confidence=info.language_probability,
            segments=segment_list
        )
    
    finally:
        os.unlink(tmp_path)


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming transcription.
    Mimics Deepgram's WebSocket protocol for easy migration.
    """
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    # Parse language from query params (like Deepgram)
    # URL format: ws://localhost:8001/ws/transcribe?language=en
    query_params = dict(websocket.query_params)
    language = query_params.get("language", None)
    
    # Audio buffer for accumulating chunks
    audio_buffer = io.BytesIO()
    sample_rate = 16000
    
    try:
        while True:
            # Receive audio chunk
            data = await websocket.receive_bytes()
            
            # Accumulate audio
            audio_buffer.write(data)
            
            # Process when we have enough audio (e.g., 1 second)
            if audio_buffer.tell() >= sample_rate * 2:  # 16-bit audio = 2 bytes per sample
                audio_buffer.seek(0)
                audio_data = audio_buffer.read()
                audio_buffer = io.BytesIO()  # Reset buffer
                
                # Convert raw bytes to numpy array
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Save to temp file for transcription
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    sf.write(tmp.name, audio_np, sample_rate)
                    
                    # Transcribe
                    segments, info = whisper_model.transcribe(
                        tmp.name,
                        language=language,
                        beam_size=5,
                        vad_filter=True
                    )
                    
                    for segment in segments:
                        # Send in Deepgram-compatible format
                        result = {
                            "type": "Results",
                            "channel_index": [0, 1],
                            "duration": segment.end - segment.start,
                            "start": segment.start,
                            "is_final": True,
                            "channel": {
                                "alternatives": [{
                                    "transcript": segment.text.strip(),
                                    "confidence": 0.95,
                                    "words": []
                                }]
                            }
                        }
                        await websocket.send_json(result)
                    
                    os.unlink(tmp.name)
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011)


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info"
    )
