import requests
from fastapi import (
    FastAPI,
    Request,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
)
import base64
from typing import Dict, List, Set
import os
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
from app.api.voicevox import synthesize
import logging
from pathlib import Path

# config.pyからトークンやAPIエンドポイントをインポート
from app.api.ai import AIClient
from app.api.db import DBClient
from app.api.message_queue import publish_message
from config import MQ_RAW_QUEUE

app = FastAPI()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
log_dir = Path(__file__).resolve().parents[2] / "logs"
log_dir.mkdir(exist_ok=True)
fh = logging.FileHandler(log_dir / "ai_responses.log")
fh.setLevel(logging.INFO)
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(fh)

# Load OpenAI credentials
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# WebSocket connections storage
active_connections: Set[WebSocket] = set()

# LINEのWebhookエンドポイント
@app.post("/api/v1/user-message")
async def post_usermessage(request: Request) -> str:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    ai_generator = AIClient()
    message = body.get("message", "")
    logger.info("User message received: %s", message)
    ai_response = ai_generator.create_response(message)
    logger.info(f"AI response: {ai_response}")
    repo = DBClient()
    repo.insert_message("me",message)
    repo.insert_message("ai",ai_response)
    return ai_response

@app.post("/api/v1/user-actions")
async def post_user_actions(request: Request) -> dict:
    """Receive browsing data from Chrome extension."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.info("Received user action: %s", data)
    publish_message(MQ_RAW_QUEUE, data)
    logger.info("User action queued")
    return {"status": "queued"}

@app.get("/api/v1/user-messages")
async def get_user_messages(user_id: str = Query(..., description="ユーザーID"), limit: int = Query(10, ge=1, le=100, description="取得件数")) -> List[Dict]:
    repo = DBClient()
    messages = repo.get_user_messages(user_id=user_id, limit=limit)
    return messages


# Endpoint to transcribe uploaded audio using OpenAI Whisper
@app.post("/api/v1/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> Dict[str, str]:
    try:
        contents = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read file")

    with tempfile.NamedTemporaryFile(suffix=".webm") as tmp:
        tmp.write(contents)
        tmp.seek(0)
        try:
            with open(tmp.name, "rb") as f:
                result = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="ja",
                )
            text = result.text.strip()
        except Exception as exc:
            logger.error("Whisper API error: %s", exc)
            raise HTTPException(status_code=500, detail="Transcription failed")

    logger.info("Transcribed audio text: %s", text)
    repo = DBClient()
    repo.insert_message("me", text)
    return {"text": text}


# WebSocket endpoint for real-time notifications
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.discard(websocket)


# HTTP endpoint to broadcast notifications to WebSocket clients
@app.post("/send-notification")
async def send_notification(request: Request) -> Dict[str, str]:
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    message = data.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    logger.info("Broadcasting notification: %s", message)

    audio_bytes = None
    try:
        audio_bytes = synthesize(message)
    except Exception as exc:
        logger.error("Failed to synthesize voice: %s", exc)

    payload = {"message": message}
    if audio_bytes:
        payload["audio"] = base64.b64encode(audio_bytes).decode()
    disconnected: Set[WebSocket] = set()
    for connection in active_connections:
        try:
            await connection.send_json(payload)
        except Exception:
            disconnected.add(connection)
    for conn in disconnected:
        active_connections.discard(conn)
    logger.info("Notification sent to %s clients", len(active_connections))
    return {"status": "sent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

