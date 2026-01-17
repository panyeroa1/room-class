import json
import os
import time
import re
import logging
from contextlib import contextmanager
from typing import Optional
from unicodedata import normalize
import numpy as np
import onnxruntime as ort

logger = logging.getLogger(__name__)

AVAILABLE_LANGS = ["en", "ko", "es", "pt", "fr"]

# --- Helper Classes from Supertonic (adapted) ---

class UnicodeProcessor:
    def __init__(self, unicode_indexer_path: str):
        with open(unicode_indexer_path, "r") as f:
            self.indexer = json.load(f)

    def _preprocess_text(self, text: str, lang: str) -> str:
        text = normalize("NFKD", text)
        # Simplified preprocessing for brevity, can be expanded
        text = re.sub(r"\s+", " ", text).strip()
        if not re.search(r"[.!?;:,'\"')\]}…。」』】〉》›»]$", text):
            text += "."
        if lang not in AVAILABLE_LANGS:
            # Fallback to english if not supported, or error
            logger.warning(f"Language {lang} not supported by Supertonic, using 'en'")
            lang = "en"
        text = f"<{lang}>" + text + f"</{lang}>"
        return text

    def _get_text_mask(self, text_ids_lengths: np.ndarray) -> np.ndarray:
        max_len = text_ids_lengths.max()
        ids = np.arange(0, max_len)
        mask = (ids < np.expand_dims(text_ids_lengths, axis=1)).astype(np.float32)
        return mask.reshape(-1, 1, max_len)

    def _text_to_unicode_values(self, text: str) -> np.ndarray:
        return np.array([ord(char) for char in text], dtype=np.uint16)

    def __call__(self, text_list: list[str], lang_list: list[str]) -> tuple[np.ndarray, np.ndarray]:
        text_list = [self._preprocess_text(t, lang) for t, lang in zip(text_list, lang_list)]
        text_ids_lengths = np.array([len(text) for text in text_list], dtype=np.int64)
        text_ids = np.zeros((len(text_list), text_ids_lengths.max()), dtype=np.int64)
        for i, text in enumerate(text_list):
            unicode_vals = self._text_to_unicode_values(text)
            text_ids[i, : len(unicode_vals)] = np.array(
                [self.indexer.get(str(val), 0) for val in unicode_vals], dtype=np.int64
            )
        text_mask = self._get_text_mask(text_ids_lengths)
        return text_ids, text_mask

class Style:
    def __init__(self, style_ttl_onnx: np.ndarray, style_dp_onnx: np.ndarray):
        self.ttl = style_ttl_onnx
        self.dp = style_dp_onnx

class TextToSpeech:
    def __init__(self, cfgs, text_processor, dp_ort, text_enc_ort, vector_est_ort, vocoder_ort):
        self.cfgs = cfgs
        self.text_processor = text_processor
        self.dp_ort = dp_ort
        self.text_enc_ort = text_enc_ort
        self.vector_est_ort = vector_est_ort
        self.vocoder_ort = vocoder_ort
        self.sample_rate = cfgs["ae"]["sample_rate"]
        self.base_chunk_size = cfgs["ae"]["base_chunk_size"]
        self.chunk_compress_factor = cfgs["ttl"]["chunk_compress_factor"]
        self.ldim = cfgs["ttl"]["latent_dim"]

    def sample_noisy_latent(self, duration: np.ndarray):
        bsz = len(duration)
        wav_len_max = duration.max() * self.sample_rate
        wav_lengths = (duration * self.sample_rate).astype(np.int64)
        chunk_size = self.base_chunk_size * self.chunk_compress_factor
        latent_len = int((wav_len_max + chunk_size - 1) / chunk_size)
        latent_dim = self.ldim * self.chunk_compress_factor
        noisy_latent = np.random.randn(bsz, latent_dim, latent_len).astype(np.float32)
        
        # Latent mask
        latent_size = chunk_size
        latent_lengths = (wav_lengths + latent_size - 1) // latent_size
        ids = np.arange(0, latent_lengths.max())
        mask = (ids < np.expand_dims(latent_lengths, axis=1)).astype(np.float32)
        latent_mask = mask.reshape(-1, 1, latent_lengths.max())
        
        noisy_latent = noisy_latent * latent_mask
        return noisy_latent, latent_mask

    def _infer(self, text_list, lang_list, style, total_step, speed=1.0):
        bsz = len(text_list)
        text_ids, text_mask = self.text_processor(text_list, lang_list)
        
        dur_onnx, *_ = self.dp_ort.run(None, {"text_ids": text_ids, "style_dp": style.dp, "text_mask": text_mask})
        dur_onnx = dur_onnx / speed
        
        text_emb_onnx, *_ = self.text_enc_ort.run(None, {"text_ids": text_ids, "style_ttl": style.ttl, "text_mask": text_mask})
        
        xt, latent_mask = self.sample_noisy_latent(dur_onnx)
        total_step_np = np.array([total_step] * bsz, dtype=np.float32)
        
        for step in range(total_step):
            current_step = np.array([step] * bsz, dtype=np.float32)
            xt, *_ = self.vector_est_ort.run(None, {
                "noisy_latent": xt, "text_emb": text_emb_onnx, "style_ttl": style.ttl,
                "text_mask": text_mask, "latent_mask": latent_mask,
                "current_step": current_step, "total_step": total_step_np,
            })
            
        wav, *_ = self.vocoder_ort.run(None, {"latent": xt})
        return wav, dur_onnx

    def __call__(self, text, lang, style, total_step=5, speed=1.0):
        # Infer single (no chunking logic handled here for brevity, assuming short text or handled upstream)
        wav, dur = self._infer([text], [lang], style, total_step, speed)
        return wav, dur

# --- Engine Wrapper Implementation ---

_tts_model = None
_voice_styles = {}
MODEL_DIR = "/app/models/supertonic"

def is_available():
    # Check if model files exist
    return os.path.exists(os.path.join(MODEL_DIR, "text_encoder.onnx"))

def load_voice_style(path):
    with open(path, "r") as f:
        data = json.load(f)
    
    # Extract
    ttl_data = np.array(data["style_ttl"]["data"], dtype=np.float32).reshape(data["style_ttl"]["dims"])
    dp_data = np.array(data["style_dp"]["data"], dtype=np.float32).reshape(data["style_dp"]["dims"])
    
    return Style(ttl_data, dp_data)

def initialize():
    global _tts_model, _voice_styles
    if _tts_model:
        return

    logger.info("Loading Supertonic models...")
    try:
        if not os.path.exists(MODEL_DIR):
            logger.error(f"Supertonic model directory not found: {MODEL_DIR}")
            return

        opts = ort.SessionOptions()
        # Use CPU for now as GPU ONNX setup can be tricky in some containers
        providers = ["CPUExecutionProvider"] 
        
        # Load configs
        with open(os.path.join(MODEL_DIR, "tts.json"), "r") as f:
            cfgs = json.load(f)
            
        proc = UnicodeProcessor(os.path.join(MODEL_DIR, "unicode_indexer.json"))
        
        dp = ort.InferenceSession(os.path.join(MODEL_DIR, "duration_predictor.onnx"), opts, providers=providers)
        te = ort.InferenceSession(os.path.join(MODEL_DIR, "text_encoder.onnx"), opts, providers=providers)
        ve = ort.InferenceSession(os.path.join(MODEL_DIR, "vector_estimator.onnx"), opts, providers=providers)
        vo = ort.InferenceSession(os.path.join(MODEL_DIR, "vocoder.onnx"), opts, providers=providers)
        
        _tts_model = TextToSpeech(cfgs, proc, dp, te, ve, vo)
        
        # Load default voice if available
        default_voice_path = os.path.join(MODEL_DIR, "voices", "M1.json")
        if os.path.exists(default_voice_path):
             _voice_styles["M1"] = load_voice_style(default_voice_path)
             
        logger.info("Supertonic initialized successfully.")
        
    except Exception as e:
        logger.error(f"Failed to initialize Supertonic: {e}")

def get_info():
    return {
        "id": "supertonic",
        "name": "Supertonic (Local ONNX)",
        "version": "2.0"
    }

def synthesize(text: str, language: str = "en", voice: str = "M1", speed: float = 1.0) -> bytes:
    if not _tts_model:
        initialize()
    if not _tts_model:
        raise RuntimeError("Supertonic model not loaded")

    # Load voice if not cache
    if voice not in _voice_styles:
        v_path = os.path.join(MODEL_DIR, "voices", f"{voice}.json")
        if os.path.exists(v_path):
            _voice_styles[voice] = load_voice_style(v_path)
        else:
            # Fallback
            if "M1" in _voice_styles:
                voice = "M1"
            else:
                raise ValueError(f"Voice {voice} not found")
    
    style = _voice_styles[voice]
    wav, dur = _tts_model(text, language, style, total_step=5, speed=speed)
    
    # Convert numpy audio to bytes (16-bit PCM WAV)
    import io
    import soundfile as sf
    
    # Remove batch dim
    wav_data = wav[0]
    
    buf = io.BytesIO()
    sf.write(buf, wav_data, _tts_model.sample_rate, format='WAV')
    return buf.getvalue()
