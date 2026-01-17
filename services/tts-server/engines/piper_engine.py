"""
Piper TTS Engine Wrapper
Fast, local neural TTS using piper-tts
"""

import io
import logging
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)

_piper_available = None

def is_available():
    """Check if piper-tts is installed"""
    global _piper_available
    if _piper_available is None:
        try:
            import piper
            _piper_available = True
        except ImportError:
            # Try CLI fallback
            try:
                result = subprocess.run(["piper", "--version"], capture_output=True, timeout=5)
                _piper_available = result.returncode == 0
            except:
                _piper_available = False
    return _piper_available

def get_info():
    return {
        "id": "piper",
        "name": "Piper TTS (Local Neural)",
        "version": "1.0",
        "languages": ["en", "de", "es", "fr", "it", "pl", "pt", "ru", "uk", "zh"],
        "features": ["fast", "offline", "multilingual"]
    }

def get_voices():
    """Return available Piper voices"""
    # Common Piper voice models
    return {
        "en_US-lessac-medium": "English (US) - Lessac Medium",
        "en_US-amy-medium": "English (US) - Amy Medium",
        "en_GB-alba-medium": "English (UK) - Alba Medium",
        "de_DE-thorsten-medium": "German - Thorsten Medium",
        "es_ES-carlfm-medium": "Spanish - Carlfm Medium",
        "fr_FR-siwis-medium": "French - Siwis Medium",
    }

def synthesize(text: str, voice: str = "en_US-lessac-medium", speed: float = 1.0) -> bytes:
    """
    Synthesize speech using Piper TTS
    
    Args:
        text: Text to synthesize
        voice: Voice model name (e.g., "en_US-lessac-medium")
        speed: Speech speed multiplier
        
    Returns:
        WAV audio bytes
    """
    if not is_available():
        raise RuntimeError("Piper TTS not available")
    
    try:
        # Try Python API first
        import piper
        
        # Piper downloads models automatically
        voice_path = None  # Let piper handle model path
        
        # Use piper's synthesize function
        synthesizer = piper.Piper(voice)
        
        # Generate audio
        audio_data = synthesizer.synthesize(text, length_scale=1.0/speed)
        
        # Convert to WAV bytes
        import soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, audio_data, 22050, format='WAV')
        return buf.getvalue()
        
    except ImportError:
        # Fallback to CLI
        logger.info("Using Piper CLI fallback")
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Run piper CLI
            cmd = [
                "piper",
                "--model", voice,
                "--output_file", tmp_path,
                "--length_scale", str(1.0/speed)
            ]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate(input=text.encode(), timeout=30)
            
            if process.returncode != 0:
                logger.error(f"Piper error: {stderr.decode()}")
                raise RuntimeError(f"Piper synthesis failed: {stderr.decode()}")
            
            # Read generated audio
            with open(tmp_path, 'rb') as f:
                return f.read()
                
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
