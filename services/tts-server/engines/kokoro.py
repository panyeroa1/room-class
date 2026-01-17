#!/usr/bin/env python3
"""
Kokoro TTS Engine
Lightweight, high-quality TTS from Sony/Hexgrad.
"""

import io
import logging
import os
from typing import Optional

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

# Lazy load
kokoro_pipeline = None


def load_model(voice: str = "af_heart"):
    """Load Kokoro model (lazy initialization)"""
    global kokoro_pipeline
    
    if kokoro_pipeline is not None:
        return True
    
    try:
        from kokoro import KPipeline
        logger.info(f"Loading Kokoro TTS with voice: {voice}")
        kokoro_pipeline = KPipeline(lang_code="a", voice=voice)
        logger.info("✓ Kokoro loaded successfully")
        return True
    except ImportError:
        logger.warning("Kokoro not installed. Run: pip install kokoro")
        return False
    except Exception as e:
        logger.error(f"Failed to load Kokoro: {e}")
        return False


def is_available() -> bool:
    """Check if Kokoro is available"""
    try:
        import kokoro
        return True
    except ImportError:
        return False


# Kokoro voice presets
VOICES = {
    # American English
    "af_heart": "American Female (Heart) - Warm",
    "af_bella": "American Female (Bella)",
    "af_nicole": "American Female (Nicole)",
    "af_sarah": "American Female (Sarah)",
    "af_sky": "American Female (Sky)",
    "am_adam": "American Male (Adam)",
    "am_michael": "American Male (Michael)",
    # British English
    "bf_emma": "British Female (Emma)",
    "bf_isabella": "British Female (Isabella)",
    "bm_george": "British Male (George)",
    "bm_lewis": "British Male (Lewis)",
    # Other languages
    "af_heart": "Default (English)",
}


def synthesize(
    text: str,
    voice: str = "af_heart",
    speed: float = 1.0
) -> bytes:
    """
    Synthesize speech.
    
    Args:
        text: Text to synthesize
        voice: Voice preset name
        speed: Speech speed multiplier
    
    Returns:
        WAV audio bytes
    """
    global kokoro_pipeline
    
    # Reload if voice changed
    if kokoro_pipeline is None or (hasattr(kokoro_pipeline, 'voice') and kokoro_pipeline.voice != voice):
        kokoro_pipeline = None
        if not load_model(voice):
            raise RuntimeError("Kokoro model not available")
    
    # Generate audio
    try:
        from kokoro import KPipeline
        
        # Create pipeline with specified voice
        pipeline = KPipeline(lang_code="a", voice=voice)
        
        # Generate
        generator = pipeline(text, speed=speed)
        
        # Collect all audio segments
        audio_segments = []
        for _, _, audio in generator:
            audio_segments.append(audio)
        
        if not audio_segments:
            raise RuntimeError("No audio generated")
        
        # Concatenate
        full_audio = np.concatenate(audio_segments)
        
        # Convert to WAV bytes
        buffer = io.BytesIO()
        sf.write(buffer, full_audio, 24000, format='WAV')
        buffer.seek(0)
        
        return buffer.read()
        
    except Exception as e:
        logger.error(f"Kokoro synthesis error: {e}")
        raise


def get_voices() -> dict:
    """Get available voices"""
    return VOICES


def get_info() -> dict:
    """Get engine info"""
    return {
        "name": "Kokoro",
        "version": "0.9.0",
        "features": ["multi_voice", "speed_control"],
        "sample_rate": 24000,
        "voices": list(VOICES.keys()),
        "available": is_available()
    }
