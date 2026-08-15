import logging
import os
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import edge_tts
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.transcriber import transcribe_audio_file, warmup_model

logger = logging.getLogger("pelocal.stt")

class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-AvaNeural"


app = FastAPI(
    title="Speech-to-Text API",
    version="1.0.0",
    description="Chunk-based multilingual transcription using an open-source Whisper model.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Pelocal STT Backend is running on Hugging Face Spaces!"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/model/warmup")
def warmup() -> dict:
    try:
        return warmup_model()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Model warmup failed: {exc}") from exc


@app.post("/api/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str | None = Form(default=None),
) -> dict:
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Upload must be an audio file.")

    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    temp_dir = Path(tempfile.gettempdir()) / "pelocal-stt"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid4().hex}{suffix}"

    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        file_size = temp_path.stat().st_size
        if file_size < 1000:
            return {
                "text": "",
                "language": None,
                "language_probability": 0,
                "duration": 0,
                "skipped": "audio chunk too small",
            }

        logger.info(
            "Transcribing upload filename=%s content_type=%s size=%s",
            audio.filename,
            audio.content_type,
            file_size,
        )
        result = await run_in_threadpool(transcribe_audio_file, temp_path, language)
        return result
    except Exception as exc:
        logger.exception(
            "Transcription failed for filename=%s content_type=%s temp_path=%s",
            audio.filename,
            audio.content_type,
            temp_path,
        )
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)


@app.post("/api/speak")
async def speak(request: TTSRequest, background_tasks: BackgroundTasks):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
        
    temp_dir = Path(tempfile.gettempdir()) / "pelocal-tts"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid4().hex}.mp3"
    
    try:
        communicate = edge_tts.Communicate(request.text, request.voice)
        await communicate.save(str(temp_path))
        
        # safely delete file after sending
        background_tasks.add_task(os.remove, str(temp_path))
        
        return FileResponse(
            path=temp_path,
            media_type="audio/mpeg",
            filename="tts_output.mp3"
        )
    except Exception as exc:
        logger.exception("TTS generation failed")
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"TTS failed: {exc}") from exc
