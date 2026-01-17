#!/usr/bin/env python3
"""
Chatterbox TTS Engine
Voice cloning with just 3 seconds of audio.
"""

import io
import logging
import tempfile
import os
from typing import Optional

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

# Lazy load to avoid import errors if not installed
chatterbox = None
model = None


def load_model():
    """Load Chatterbox model (lazy initialization)"""
    global chatterbox, model
    
    if model is not None:
        return True
    
    try:
        from chatterbox.tts import ChatterboxTTS
        logger.info("Loading Chatterbox TTS model...")
        model = ChatterboxTTS.from_pretrained(device="auto")
        logger.info("✓ Chatterbox loaded successfully")
        return True
    except ImportError:
        logger.warning("Chatterbox not installed. Run: pip install chatterbox-tts")
        return False
    except Exception as e:
        logger.error(f"Failed to load Chatterbox: {e}")
        return False


def is_available() -> bool:
    """Check if Chatterbox is available"""
    try:
        import chatterbox
        return True
    except ImportError:
        return False


def synthesize(
    text: str,
    voice_sample: Optional[str] = None,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5
) -> bytes:
    """
    Synthesize speech with optional voice cloning.
    
    Args:
        text: Text to synthesize
        voice_sample: Path to voice sample audio for cloning (3+ seconds)
        exaggeration: Emotion exaggeration (0.0-1.0)
        cfg_weight: CFG weight for generation quality
    
    Returns:
        WAV audio bytes
    """
    if not load_model():
        raise RuntimeError("Chatterbox model not available")
    
    # Generate audio
    if voice_sample and os.path.exists(voice_sample):
        # Voice cloning mode
        audio = model.generate(
            text,
            audio_prompt=voice_sample,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight
        )
    else:
        # Default voice
        audio = model.generate(
            text,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight
        )
    
    # Convert to WAV bytes
    audio_np = audio.cpu().numpy().squeeze()
    
    buffer = io.BytesIO()
    sf.write(buffer, audio_np, 24000, format='WAV')
    buffer.seek(0)
    
    return buffer.read()


def get_info() -> dict:
    """Get engine info"""
    return {
        "name": "Chatterbox",
        "version": "0.1.0",
        "features": ["voice_cloning", "emotion_control"],
        "sample_rate": 24000,
        "available": is_available()
    }
