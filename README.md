# Pelocal Multilingual Speech AI

A self-hostable multilingual speech API with a React web interface. The
backend accepts short audio uploads or browser-recorded chunks, transcribes
them with faster-whisper, and can generate MP3 speech through Edge TTS.

## What is implemented

- Browser microphone recording with MediaRecorder.
- Multipart audio transcription through FastAPI.
- Optional Whisper language hints and detected-language responses.
- Supported audio validation, size limits, temporary-file cleanup, and bounded
  inference admission.
- Text-to-speech generation with an allow-listed Edge TTS voice set.
- Browser-local speech history using IndexedDB. History is not uploaded to the
  backend and is scoped to the current browser origin/profile.
- Health, readiness, and explicit model-warmup endpoints.
- Unit/regression tests for API behavior, persistence, evaluation metrics, and
  manifest validation.
- A separate evaluation framework for reproducible datasets and Whisper
  comparisons. Evaluation audio and generated results remain local.

Indic-Transcribe is experimental research work only. It is not integrated into
the production API, and there is no provider routing or automatic model
selection.

## Architecture

```text
React + Vite browser
        |
        | multipart audio / JSON TTS requests
        v
FastAPI backend
  |-- faster-whisper model cache and serialized inference
  |-- Edge TTS provider
  |-- temporary upload/output files
        |
        +-- browser IndexedDB stores local history only
```

### Technology

- Python 3.11+ recommended for the Docker image; local development supports
  the configured Python environment.
- FastAPI and Uvicorn.
- faster-whisper 1.1.1 with `av<19`.
- React 19, Vite, and Vitest.
- Edge TTS.
- Docker Compose for the backend/frontend stack.

## Production inference configuration

The default production configuration is:

```text
WHISPER_MODEL_SIZE=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

The model is loaded lazily and cached in the backend process. The first
transcription or warmup may download model files from Hugging Face and requires
enough disk space and RAM. Configure these values through environment
variables; do not commit model weights or caches.

The backend calls faster-whisper with `task="transcribe"`, optional language
selection, VAD enabled, `beam_size=1`, and
`condition_on_previous_text=False`. The production default is not changed by
the experimental evaluation scripts.

## API

The interactive API contract is available at `http://localhost:8000/docs`
when the backend is running.

### `GET /`

Returns service information:

```json
{"message":"Pelocal Speech AI API is running."}
```

### `GET /health`

Lightweight liveness check. It does not load the model:

```json
{"status":"ok"}
```

### `GET /ready`

Reports whether the configured model is already loaded:

```json
{"status":"not_ready","model_loaded":false,"model_size":"small"}
```

### `POST /api/model/warmup`

Loads the configured model explicitly. This may download model files and can
fail when the host does not have enough memory.

### `POST /api/transcribe`

Send `multipart/form-data` with:

- `audio`: required audio file.
- `language`: optional language hint such as `hi` or `en`.
- `sequence`: optional non-negative client sequence number.

Example:

```bash
curl -X POST http://localhost:8000/api/transcribe \
  -F "audio=@sample.wav" \
  -F "language=hi" \
  -F "sequence=0"
```

The response includes `text`, detected `language`,
`language_probability`, `duration`, `no_speech_probability`, `skipped`, and
the supplied `sequence`.

### `POST /api/speak`

Send JSON text and an allow-listed voice:

```bash
curl -X POST http://localhost:8000/api/speak \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Hello from Pelocal\",\"voice\":\"en-US-AvaNeural\"}" \
  --output speech.mp3
```

The response is an `audio/mpeg` MP3. TTS requires network access to the Edge
TTS service.

## Run locally

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

The `.env` file is local-only. The first model use may download the configured
Whisper model. For a lower-memory development run, set a smaller model
explicitly in the local `.env`, for example `WHISPER_MODEL_SIZE=tiny`; this
does not change the production default.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Set `VITE_API_BASE_URL` when the backend is not
running at `http://localhost:8000`.

## Docker Compose

Docker Desktop is required:

```powershell
docker compose build
docker compose up -d
docker compose ps
```

Then check:

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

The backend runs as a non-root `appuser`. Model files are stored in the named
`pelocal-whisper-model-cache` volume. The frontend waits for the backend
healthcheck before starting. `docker compose down` stops containers but
preserves the named model cache; remove that volume only when you intentionally
want to redownload model files.

## Configuration

Copy [backend/.env.example](backend/.env.example) to a local `.env` and
adjust values as needed. Important settings include:

- `WHISPER_MODEL_SIZE`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`
- `CORS_ORIGINS`
- `MAX_UPLOAD_SIZE_BYTES`
- `MAX_ADMITTED_INFERENCE_REQUESTS`
- `SUPPORTED_AUDIO_EXTENSIONS`
- `TEMP_DIRECTORY`
- `TTS_DEFAULT_VOICE`, `TTS_ALLOWED_VOICES`,
  `TTS_MAX_TEXT_CHARACTERS`

Never put Hugging Face tokens, API keys, or real credentials in `.env.example`,
the README, notebooks, or source control.

## Tests and builds

Backend tests:

```powershell
python -m pytest backend/tests -q
python -m compileall -q backend/app backend/tests
```

Frontend tests and production build:

```powershell
cd frontend
npm test
npm run build
```

These commands do not require downloading Whisper weights unless a test or
explicit warmup invokes the model.

## Evaluation framework

Evaluation source code is under
[backend/app/evaluation](backend/app/evaluation). Dataset preparation,
provenance, validation, and benchmark instructions are documented in
[evaluation/README.md](evaluation/README.md) and
[docs/evaluation.md](docs/evaluation.md).

Validate a locally supplied manifest from the backend directory:

```powershell
cd backend
python -m app.evaluation.validate_manifest ..\evaluation\dataset\manifests\v1.json
```

Evaluation audio under `evaluation/dataset/audio/` and generated JSON/CSV
results under `evaluation/dataset/results/` are intentionally excluded from
Git. They may contain private recordings, transcripts, checksums, and
benchmark outputs.

The Indic-Transcribe Colab pilot notebook is
[notebooks/indic_transcribe_core_pilot.ipynb](notebooks/indic_transcribe_core_pilot.ipynb).
It is experimental only, uses a pinned gated model revision, and must not be
run on the local Windows host.

## Limitations

- Whisper accuracy varies substantially by language, recording quality,
  decoding configuration, and model size.
- The 15-sample Kathbath pilot found correct language detection but frequent
  output-script mismatches for Whisper Base.
- The corrected evaluation CER is Unicode-normalized code-point CER, not
  grapheme-cluster CER. WER is whitespace-token based and is a coarse metric
  for Indic languages.
- The configured `small` model may exceed available memory on development
  machines.
- Browser history is local to one browser origin/profile and can be removed by
  browser storage cleanup or quota limits.
- Edge TTS depends on an external network service.
- This project is not a distributed inference system, database-backed history
  service, WebSocket streaming service, or hosted commercial API.

## Security and privacy

- Uploads and generated TTS files are temporary and removed after processing.
- Request logs contain request metadata and generated request IDs, not audio
  contents or transcripts.
- Do not upload sensitive recordings without the required consent and
  retention controls.
- Restrict CORS origins before exposing the service beyond local development.
- Do not expose the model cache, `.env`, Hugging Face tokens, or evaluation
  audio through a public deployment.

## Documentation and contribution

See [docs/deployment.md](docs/deployment.md),
[docs/concurrency.md](docs/concurrency.md), and the engineering audit under
[docs/audit](docs/audit) for additional context. Keep production changes,
evaluation experiments, and private data separate. Add or update regression
tests for behavior changes and run the relevant backend/frontend checks before
opening a pull request.

No project `LICENSE` file is currently present; obtain maintainer approval
before selecting or adding a project license. Third-party model, dataset, and
Edge TTS terms remain applicable independently of the project source.

## Roadmap

Potential future work, not currently implemented:

1. Evaluate native-script Indic ASR candidates in an approved GPU environment.
2. Improve production observability and deployment hardening.
3. Consider authenticated, scalable inference only after a separate design and
   licensing review.
