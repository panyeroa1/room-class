#!/usr/bin/env python3
"""
Coqui XTTS Engine
Multi-lingual TTS with voice cloning (6 seconds sample).
"""

import io
import logging
import os
from typing import Optional

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

# Lazy load
tts_model = None


def load_model():
    """Load Coqui XTTS model (lazy initialization)"""
    global tts_model
    
    if tts_model is not None:
        return True
    
    try:
        from TTS.api import TTS
        logger.info("Loading Coqui XTTS model...")
        tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        logger.info("✓ Coqui XTTS loaded successfully")
        return True
    except ImportError:
        logger.warning("Coqui TTS not installed. Run: pip install TTS")
        return False
    except Exception as e:
        logger.error(f"Failed to load Coqui XTTS: {e}")
        return False


def is_available() -> bool:
    """Check if Coqui TTS is available"""
    try:
        from TTS.api import TTS
        return True
    except ImportError:
        return False


# Supported languages (XTTS v2)
LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "pl": "Polish",
    "tr": "Turkish",
    "ru": "Russian",
    "nl": "Dutch",
    "cs": "Czech",
    "ar": "Arabic",
    "zh-cn": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "hu": "Hungarian",
    "hi": "Hindi"
}


def synthesize(
    text: str,
    language: str = "en",
    voice_sample: Optional[str] = None
) -> bytes:
    """
    Synthesize speech with optional voice cloning.
    
    Args:
        text: Text to synthesize
        language: Language code (en, es, fr, etc.)
        voice_sample: Path to voice sample for cloning (6+ seconds recommended)
    
    Returns:
        WAV audio bytes
    """
    if not load_model():
        raise RuntimeError("Coqui XTTS model not available")
    
    # Map language code
    lang = language.lower()
    if lang not in LANGUAGES:
        lang = "en"  # Fallback
    
    try:
        import tempfile
        
        # Generate to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            if voice_sample and os.path.exists(voice_sample):
                # Voice cloning mode
                tts_model.tts_to_file(
                    text=text,
                    file_path=tmp.name,
                    speaker_wav=voice_sample,
                    language=lang
                )
            else:
                # Use default speaker
                tts_model.tts_to_file(
                    text=text,
                    file_path=tmp.name,
                    language=lang
                )
            
            # Read and return
            with open(tmp.name, 'rb') as f:
                audio_bytes = f.read()
            
            os.unlink(tmp.name)
            return audio_bytes
            
    except Exception as e:
        logger.error(f"Coqui synthesis error: {e}")
        raise


def get_languages() -> dict:
    """Get supported languages"""
    return LANGUAGES


def get_info() -> dict:
    """Get engine info"""
    return {
        "name": "Coqui XTTS",
        "version": "2.0",
        "features": ["voice_cloning", "multi_language"],
        "sample_rate": 24000,
        "languages": list(LANGUAGES.keys()),
        "available": is_available()
    }
