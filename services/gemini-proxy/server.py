import os
import asyncio
import json
import logging
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gemini-proxy")

app = FastAPI()

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not set!")

client = None
if GEMINI_API_KEY:
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=GEMINI_API_KEY,
    )

CONFIG_STT = types.LiveConnectConfig(
    response_modalities=["TEXT"], # We only want text for STT
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
        )
    ),
)

CONFIG_TTS = types.LiveConnectConfig(
    response_modalities=["AUDIO"], # We want audio for TTS
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
        )
    ),
)

@app.websocket("/ws/stt")
async def websocket_stt(websocket: WebSocket):
    """
    STT Endpoint: Receives Audio -> Sends Text
    """
    await websocket.accept()
    logger.info("STT Connection accepted")
    
    if not client:
        await websocket.close(code=1008, reason="API Key missing")
        return

    try:
        # Start Gemini Session
        async with client.aio.live.connect(model=MODEL, config=CONFIG_STT) as session:
            
            # Helper to receive from Gemini
            async def receive_from_gemini():
                while True:
                    try:
                        turn = session.receive()
                        async for response in turn:
                            if text := response.text:
                                await websocket.send_json({"type": "transcript", "text": text, "is_final": True})
                    except Exception as e:
                        logger.error(f"Gemini receive error: {e}")
                        break

            receive_task = asyncio.create_task(receive_from_gemini())

            # Send prompt to instruct it to act as transcriber
            await session.send(input="You are a precise transcriber. Repeat exactly what you hear. Do not answer questions. Just transcribe.", end_of_turn=True)

            # Receive Audio from Client
            try:
                while True:
                    data = await websocket.receive_bytes()
                    # Gemini expects specific chunk format or just pcm? 
                    # The python script used "mime_type": "audio/pcm"
                    await session.send(input={"data": data, "mime_type": "audio/pcm"})
            except WebSocketDisconnect:
                logger.info("Client disconnected")
            except Exception as e:
                logger.error(f"WebSocket Loop Error: {e}")
            finally:
                receive_task.cancel()

    except Exception as e:
        logger.error(f"Session Error: {e}")
        traceback.print_exc()
        await websocket.close(code=1011, reason=str(e))


@app.websocket("/ws/tts")
async def websocket_tts(websocket: WebSocket):
    """
    TTS Endpoint: Receives Text -> Sends Audio
    """
    await websocket.accept()
    logger.info("TTS Connection accepted")
    
    if not client:
        await websocket.close(code=1008, reason="API Key missing")
        return

    try:
        # Start Gemini Session
        async with client.aio.live.connect(model=MODEL, config=CONFIG_TTS) as session:
            
            # Helper to receive audio from Gemini
            async def receive_from_gemini():
                while True:
                    try:
                        turn = session.receive()
                        async for response in turn:
                            if data := response.data:
                                # Send audio bytes directly
                                await websocket.send_bytes(data)
                    except Exception as e:
                        logger.error(f"Gemini receive error: {e}")
                        break
            
            receive_task = asyncio.create_task(receive_from_gemini())

            # Wait for text input from client
            try:
                while True:
                    msg = await websocket.receive_json()
                    text = msg.get("text")
                    if text:
                        # Instruct it to say the text
                        await session.send(input=f"Please say clearly: {text}", end_of_turn=True)
            except WebSocketDisconnect:
                logger.info("Client disconnected")
            except Exception as e:
                logger.error(f"WebSocket Loop Error: {e}")
            finally:
                receive_task.cancel()

    except Exception as e:
        logger.error(f"Session Error: {e}")
        await websocket.close(code=1011, reason=str(e))
