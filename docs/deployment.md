# Docker deployment

Docker packages the application and its dependencies into images. A container
is a running instance of an image. Docker Compose starts the backend and
frontend together with the correct ports, health dependency, and model-cache
volume.

## Architecture

- **Backend container:** FastAPI/Uvicorn on `http://localhost:8000`.
- **Frontend container:** Nginx serves the compiled React application on
  `http://localhost:5173`.
- **Model volume:** `pelocal-whisper-model-cache` is mounted at
  `/opt/model-cache`. Whisper downloads its files there on the first warmup or
  transcription request and reuses them after container recreation.

The browser uses `http://localhost:8000`, not the Compose service name
`backend`. Service names such as `backend` are resolvable inside the Compose
network, but not by a browser running on the host. The frontend image receives
the browser-facing URL through the `VITE_API_BASE_URL` build argument.

## Prerequisites

- Docker Desktop with Docker Compose
- At least several GB of disk space for the Whisper model cache
- Adequate memory for the selected Whisper model

The default deployment uses the CPU `small` model. GPU deployment is not
configured by this project.

## Start with Compose

From the repository root in PowerShell:

```powershell
docker compose build
docker compose up -d
```

Open:

```text
http://localhost:5173
```

The first model use may download Whisper weights into the named volume. This
does not happen during image build, so image builds remain independent from
the model cache and the downloaded files persist across container recreation.

## Verify the deployment

```powershell
docker compose ps
Invoke-WebRequest http://localhost:8000/health
Invoke-WebRequest http://localhost:8000/ready
```

`/health` is a lightweight liveness check and does not load Whisper. `/ready`
reports `not_ready` until the model has been loaded. Use the frontend or call
`POST /api/model/warmup` to load it.

Inspect logs:

```powershell
docker compose logs -f backend
docker compose logs -f frontend
```

## Configuration

Create a root `.env` file only if you need to override Compose defaults. Do
not commit secrets or local `.env` files.

```text
WHISPER_MODEL_SIZE=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
MAX_ADMITTED_INFERENCE_REQUESTS=2
MAX_UPLOAD_SIZE_BYTES=15728640
VITE_API_BASE_URL=http://localhost:8000
```

Backend runtime settings are documented in
[backend/.env.example](../backend/.env.example). The frontend API URL is a
Vite build-time setting, so rebuild the frontend image after changing it:

```powershell
docker compose build frontend
docker compose up -d frontend
```

## Stop and rebuild

```powershell
docker compose down
docker compose build --no-cache
docker compose up -d
```

`docker compose down` stops and removes containers but preserves the named
model-cache volume. `docker compose down -v` also deletes that volume, which
forces Whisper to download the model again and should not be used for normal
cleanup.

## Local development without Docker

The backend and frontend can still be run directly using the instructions in
[backend/README.md](../backend/README.md) and
[README.md](../README.md). Docker is an additional reproducible deployment
path, not a replacement for local development.

## Common issues

- **Frontend cannot reach the API:** verify that port `8000` is exposed and
  that `VITE_API_BASE_URL` is a browser-resolvable URL, not `http://backend:8000`.
- **Backend is unhealthy:** inspect `docker compose logs backend`; model
  loading is not part of the health check.
- **Slow first transcription:** the model is being downloaded or initialized.
  Later requests reuse the named cache volume.
- **Out-of-memory errors:** choose a smaller Whisper model or provide more
  memory to Docker Desktop.
- **TTS failures:** Edge TTS still requires network access from the backend
  container; Docker does not provide an offline TTS service.
