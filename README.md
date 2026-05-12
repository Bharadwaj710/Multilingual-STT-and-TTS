# Speech-to-Text & TTS System

A multilingual speech-to-text web application.

## Problem Statement

Build a web application where a user speaks in real time and the system transcribes the speech. Speech may be multilingual, for example Hindi, English, or a Hindi-English mix.

### Functional Requirements

- Capture microphone audio in the browser.
- Send audio to a backend speech-to-text service.
- Transcribe spoken words and show text to the user.
- Support multilingual input.
- Prefer a self-deployed open-source speech-to-text model.

### Non-Functional Requirements

- Low-latency enough for a demo.
- Simple browser UI.
- Backend should expose a clean API.
- Model should be practical to run locally and deploy.
- Implementation should be recruiter-demo friendly.

### Constraints

- Real-time transcription is requested, but full streaming is not required for a short assignment demo.
- Open-source STT is preferred.
- Multilingual support is important.
- Keep the solution practical and executable.

## Step 2: Solution Breakdown

### Architecture

- Frontend: React + Vite UI using `MediaRecorder`.
- Backend: FastAPI API with `/api/transcribe`.
- AI model: `faster-whisper`, an optimized open-source Whisper implementation.
- Audio flow: Browser records WebM chunks and backend transcribes each chunk independently.

### Data Flow

1. User clicks `Start recording`.
2. Browser asks for microphone permission.
3. `MediaRecorder` captures audio in 5-second chunks.
4. Each chunk is sent as `multipart/form-data` to `POST /api/transcribe`.
5. FastAPI saves the chunk temporarily.
6. Whisper transcribes the audio using auto-detect or the selected language hint.
7. Backend returns transcript text and detected language.
8. Frontend appends the returned text to the transcript panel.

### Key Components

- `frontend/src/App.tsx`: microphone control, chunk upload, transcript rendering.
- `frontend/src/styles.css`: responsive UI styling.
- `backend/app/main.py`: FastAPI routes, CORS, file upload handling.
- `backend/app/transcriber.py`: Whisper model loading and transcription.
- `backend/app/config.py`: environment-driven configuration.

### Tech Stack Justification

- FastAPI: simple, fast Python API framework with strong file upload support.
- faster-whisper: open-source, multilingual, faster and lighter than standard Whisper in many CPU deployments.
- React + Vite: quick demo setup, good browser API integration, easy Vercel deployment.
- MediaRecorder: native browser microphone recording without extra frontend libraries.
- Multipart upload: simple and reliable for short audio chunks.

## Step 3: Implementation Plan

### MVP

1. Create FastAPI backend with health check.
2. Add `/api/transcribe` accepting audio upload.
3. Integrate Whisper model with auto language detection.
4. Create React UI with start/stop recording.
5. Send 5-second chunks to backend.
6. Append transcript chunks in UI.
7. Add local run and deployment docs.

### Enhanced Version

1. Add WebSocket streaming for lower latency.
2. Add speaker/session IDs and transcript persistence.
3. Add language selection override.
4. Add punctuation cleanup and chunk merging.
5. Add queue-based background transcription for scale.
6. Add authentication for deployed demos.

## Step 4: Project Structure

```text
Pelocal-assesment/
  backend/
    app/
      __init__.py
      config.py
      main.py
      transcriber.py
    requirements.txt
    README.md
  frontend/
    src/
      App.tsx
      styles.css
    index.html
    package.json
    README.md
  README.md
```

## Step 5: Implementation

The implementation is included in this repository:

- Backend API: `backend/app/main.py`
- Whisper wrapper: `backend/app/transcriber.py`
- Frontend recorder: `frontend/src/App.tsx`
- Frontend styling: `frontend/src/styles.css`

## Step 6: Real-Time Simplification

This demo uses chunk-based processing instead of true streaming. The frontend records 5-second audio chunks and sends each chunk to the backend.

This is acceptable for the assignment because:

- It feels near real time for a recruiter demo.
- It avoids WebSocket and streaming audio complexity.
- It is easier to debug and deploy.
- It still proves the core requirement: microphone input to multilingual transcription output.

## Step 7: Improvements

### Performance

- Use `base` for the default demo.
- Use `tiny` only when the machine is too slow.
- Use `small` or `medium` for better multilingual accuracy.
- Run the model on GPU when available.
- Keep the model loaded in memory instead of loading per request.
- Add request queueing for concurrent users.

### UI

- Add live waveform visualization.
- Add continuous merged transcript view.
- Add download transcript button.
- Add language confidence display toggle.
- Add recording timer.

### Scalability

- Separate API and worker processes.
- Store uploaded chunks in object storage for async processing.
- Use Redis Queue, Celery, or Dramatiq for background jobs.
- Add autoscaling workers for transcription-heavy traffic.
- Add rate limiting and request size limits.

### Multilingual Handling

- Keep auto language detection for mixed-language input.
- Use the language hint dropdown for better Hindi or regional-language accuracy.
- Prefer Whisper `small` or larger for Hindi-English code-switching.
- Add text normalization for Hindi, English, and Hinglish output.

## Step 8: Run and Deploy

### Run Locally

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Optional but recommended before first run:

```bash
set HF_TOKEN=your_huggingface_token
```

The token is not required for public Whisper models, but it avoids unauthenticated Hugging Face rate limits. The first request downloads model files, so keep the backend running until the download finishes.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```
# Pelcol-Multilingual
