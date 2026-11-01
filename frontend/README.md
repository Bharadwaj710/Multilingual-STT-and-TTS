# Frontend

React + Vite app that records microphone audio with `MediaRecorder`, sends 2.5-second chunks to the backend, and displays returned transcript chunks.

## Run Locally

```bash
cd frontend
npm install
npm run dev
```

Optional environment variable:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Local history

Successful transcription chunks and generated speech are saved in the browser's
IndexedDB storage. They are restored after refresh and are never uploaded as
history to the backend. The history panel supports replay and individual or
complete deletion.

This storage is local to the current browser profile. Browser settings,
private browsing, quota limits, or manual site-data cleanup can still remove
it. If storage is unavailable or full, the application reports the save or
restore error instead of claiming that a record was persisted.
