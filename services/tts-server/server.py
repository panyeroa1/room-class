#!/usr/bin/env python3
"""
Multi-Engine TTS Server
Supports Chatterbox (voice cloning), Kokoro (high quality), and Coqui XTTS (multilingual).
Replaces cloud Cartesia TTS with local inference.
"""

import io
import json
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from enum import Enum
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings

# Import engines
from engines import chatterbox, kokoro, coqui, supertonic_engine, piper_engine

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TTSEngine(str, Enum):
    CHATTERBOX = "chatterbox"
    KOKORO = "kokoro"
    COQUI = "coqui"
    SUPERTONIC = "supertonic"
    PIPER = "piper"
    AUTO = "auto"


class Settings(BaseSettings):
    """Server configuration"""
    default_engine: TTSEngine = TTSEngine.KOKORO  # Kokoro is lightweight and high quality
    host: str = "0.0.0.0"
    port: int = 8002
    voices_dir: str = "./voices"
    
    class Config:
        env_prefix = "TTS_"


settings = Settings()

# Track loaded engines
loaded_engines = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize engines on startup"""
    logger.info("Initializing TTS engines...")
    
    # Check availability
    if kokoro.is_available():
        logger.info("  ✓ Kokoro available")
        loaded_engines["kokoro"] = True
    else:
        logger.info("  ✗ Kokoro not installed")
    
    if chatterbox.is_available():
        logger.info("  ✓ Chatterbox available")
        loaded_engines["chatterbox"] = True
    else:
        logger.info("  ✗ Chatterbox not installed")
    
    if coqui.is_available():
        logger.info("  ✓ Coqui XTTS available")
        loaded_engines["coqui"] = True
    else:
        logger.info("  ✗ Coqui XTTS not installed")

    if supertonic_engine.is_available():
        logger.info("  ✓ Supertonic available")
        loaded_engines["supertonic"] = True
    else:
        logger.info("  ✗ Supertonic models not found")

    if piper_engine.is_available():
        logger.info("  ✓ Piper available")
        loaded_engines["piper"] = True
    else:
        logger.info("  ✗ Piper not installed")
    
    # Ensure voices directory exists
    os.makedirs(settings.voices_dir, exist_ok=True)
    
    yield
    
    logger.info("TTS server shutting down")


app = FastAPI(
    title="Eburon TTS Server",
    description="Local text-to-speech API with multiple engines",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SynthesizeRequest(BaseModel):
    text: str
    engine: TTSEngine = TTSEngine.AUTO
    language: str = "en"
    voice: Optional[str] = None
    voice_sample_id: Optional[str] = None
    speed: float = 1.0
    exaggeration: float = 0.5  # Chatterbox emotion


class HealthResponse(BaseModel):
    status: str
    engines: dict


class VoiceInfo(BaseModel):
    id: str
    name: str
    engine: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check with engine status"""
    return HealthResponse(
        status="healthy",
        engines={
            "kokoro": kokoro.is_available(),
            "chatterbox": chatterbox.is_available(),
            "coqui": coqui.is_available(),
            "supertonic": supertonic_engine.is_available()
        }
    )


@app.get("/engines")
async def list_engines():
    """List available TTS engines with their capabilities"""
    engines = []
    
    if kokoro.is_available():
        engines.append(kokoro.get_info())
    if chatterbox.is_available():
        engines.append(chatterbox.get_info())
    if coqui.is_available():
        engines.append(coqui.get_info())
    if supertonic_engine.is_available():
        engines.append(supertonic_engine.get_info())
    
    return {"engines": engines, "default": settings.default_engine.value}


@app.get("/voices")
async def list_voices():
    """List available voices across all engines"""
    voices = []
    
    # Kokoro preset voices
    if kokoro.is_available():
        for voice_id, name in kokoro.get_voices().items():
            voices.append(VoiceInfo(id=voice_id, name=name, engine="kokoro"))
            
    # Supertonic preset voices
    if supertonic_engine.is_available():
        # Hardcoded for now based on what we included
        voices.append(VoiceInfo(id="M1", name="Supertonic M1", engine="supertonic"))
        voices.append(VoiceInfo(id="F1", name="Supertonic F1", engine="supertonic"))
    
    # Custom cloned voices
    for filename in os.listdir(settings.voices_dir):
        if filename.endswith(('.wav', '.mp3', '.flac')):
            voice_id = os.path.splitext(filename)[0]
            voices.append(VoiceInfo(
                id=voice_id,
                name=f"Cloned: {voice_id}",
                engine="chatterbox/coqui"
            ))
    
    return {"voices": voices}


@app.post("/voices/upload")
async def upload_voice(
    voice_id: str = Form(...),
    audio: UploadFile = File(...)
):
    """Upload a voice sample for cloning"""
    # Validate
    if not voice_id.isalnum():
        raise HTTPException(400, "Voice ID must be alphanumeric")
    
    # Save audio
    voice_path = os.path.join(settings.voices_dir, f"{voice_id}.wav")
    
    content = await audio.read()
    with open(voice_path, 'wb') as f:
        f.write(content)
    
    return {"status": "uploaded", "voice_id": voice_id, "path": voice_path}


@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    """
    Synthesize speech from text.
    Returns WAV audio.
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(400, "Text cannot be empty")
    
    # Determine engine
    engine = request.engine
    if engine == TTSEngine.AUTO:
        # Auto-select based on requirements
        if request.voice_sample_id:
            # Voice cloning needed
            engine = TTSEngine.CHATTERBOX if chatterbox.is_available() else TTSEngine.COQUI
        else:
            # Default to Kokoro (fastest, best quality for preset voices)
            engine = TTSEngine.KOKORO if kokoro.is_available() else TTSEngine.COQUI
    
    # Get voice sample path if cloning
    voice_sample_path = None
    if request.voice_sample_id:
        voice_sample_path = os.path.join(settings.voices_dir, f"{request.voice_sample_id}.wav")
        if not os.path.exists(voice_sample_path):
            raise HTTPException(404, f"Voice sample not found: {request.voice_sample_id}")
    
    try:
        if engine == TTSEngine.KOKORO:
            if not kokoro.is_available():
                raise HTTPException(503, "Kokoro engine not available")
            audio_bytes = kokoro.synthesize(
                text,
                voice=request.voice or "af_heart",
                speed=request.speed
            )
        
        elif engine == TTSEngine.CHATTERBOX:
            if not chatterbox.is_available():
                raise HTTPException(503, "Chatterbox engine not available")
            audio_bytes = chatterbox.synthesize(
                text,
                voice_sample=voice_sample_path,
                exaggeration=request.exaggeration
            )
        
        elif engine == TTSEngine.COQUI:
            if not coqui.is_available():
                raise HTTPException(503, "Coqui engine not available")
            audio_bytes = coqui.synthesize(
                text,
                language=request.language,
                voice_sample=voice_sample_path
            )
        
        elif engine == TTSEngine.COQUI:
            if not coqui.is_available():
                raise HTTPException(503, "Coqui engine not available")
            audio_bytes = coqui.synthesize(
                text,
                language=request.language,
                voice_sample=voice_sample_path
            )

        elif engine == TTSEngine.SUPERTONIC:
            if not supertonic_engine.is_available():
                 raise HTTPException(503, "Supertonic engine not available")
            audio_bytes = supertonic_engine.synthesize(
                text,
                language=request.language,
                voice=request.voice or "M1",
                speed=request.speed
            )
        
        else:
            raise HTTPException(400, f"Unknown engine: {engine}")
        
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=speech.wav"
            }
        )
    
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(500, f"Synthesis failed: {str(e)}")


@app.post("/tts/bytes")
async def tts_bytes_compat(
    model_id: str = Form("sonic-3-latest"),
    transcript: str = Form(...),
    voice_id: str = Form(None),
    language: str = Form("en")
):
    """
    Cartesia-compatible endpoint for easy migration.
    Matches Cartesia API format: POST /tts/bytes
    """
    # Map to our synthesize request
    request = SynthesizeRequest(
        text=transcript,
        engine=TTSEngine.AUTO,
        language=language,
        voice=voice_id
    )
    
    return await synthesize(request)


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info"
    )
