# Implementation Status Matrix

Status reflects repository evidence, not README claims or installed dependencies. “UNVERIFIED” means code was not able to prove end-to-end behavior in this audit; model inference and external Edge TTS were deliberately not invoked.

| Feature | Status | Implementation Evidence | Technical Details | Limitations |
|---|---|---|---|---|
| Audio recording | IMPLEMENTED | `App.jsx:193-249` | `getUserMedia` + `MediaRecorder` with shared microphone stream. | Requires browser permission/secure context; no input-device settings or recording recovery. |
| Audio upload | IMPLEMENTED | `App.jsx:150-190`; `main.py:58-103` | Multipart POST field `audio`, optional `language`. | No request/file/duration limit; client MIME trusted. |
| Audio chunking | IMPLEMENTED | `CHUNK_MS=5000`; `recordSegment()` | Sequential discrete recorder sessions, each nominally 5 seconds. | Not framed streaming; gap/overlap/reordering risks; README/frontend README disagree on duration. |
| Audio preprocessing | PARTIALLY IMPLEMENTED | `transcriber.py:45-49` | Library VAD filter, min silence 700 ms, pad 300 ms. | No explicit resample, normalize, denoise, codec probing, or duration control. |
| Speech recognition | IMPLEMENTED | `WhisperModel.transcribe` at `transcriber.py:41-52` | `faster-whisper`, task `transcribe`, beam size 1. | Runtime model download/performance and true inference output unverified in this audit. |
| Automatic language detection | IMPLEMENTED | `info.language` returned at `transcriber.py:77-78` | Whisper's per-chunk language result/probability. | No separate LID, smoothing, confidence policy, or evaluation. |
| Multilingual support | PARTIALLY IMPLEMENTED | multilingual Whisper configuration; UI language options | Hints include en/hi/mr/ta/te; auto mode exists. | Model capability is not a tested language support guarantee. |
| Indian language support | PARTIALLY IMPLEMENTED | `LANGUAGE_OPTIONS` and multilingual Whisper | Hindi, Marathi, Tamil, Telugu selectable. | No corpus, WER, script/punctuation strategy or dialect/code-switch validation. |
| Code-mixed speech | EXPERIMENTAL | UI copy and auto/hint forwarding | Whisper may emit mixed speech text. | No routing, language-span labels, prompt/context, evaluation, or merge strategy. |
| Translation | NOT IMPLEMENTED | No route/import/model/UI workflow found | — | No translation capability. |
| Text-to-Speech | IMPLEMENTED | `/api/speak`; `edge_tts.Communicate`; `playTTS()` | Server synthesizes temporary MP3; browser plays it. | External provider; no timeout, auth/rate controls, or test. |
| Voice selection | PARTIALLY IMPLEMENTED | `TTS_VOICES` passed as `voice` | Five hardcoded provider identifiers. | No backend allowlist; “Auto-Detect” is actually Hindi; labels do not cover Hindi explicitly. |
| Real-time processing | PARTIALLY IMPLEMENTED | recurring 5-sec uploads | Near-real-time chunk processing UI. | Not real-time streaming; processing begins only after a chunk stops/uploads. |
| Streaming transcription | NOT IMPLEMENTED | No persistent audio protocol / partial results | — | HTTP batch requests only. |
| WebSocket communication | NOT IMPLEMENTED | No WebSocket route/client | — | Explicitly a future idea in root README. |
| API architecture | PARTIALLY IMPLEMENTED | 4 direct FastAPI routes in `main.py` | `/`, `/health`, warmup, transcribe, speak. | No versioning, schemas, service layers, OpenAPI examples or stable errors. |
| Error handling | PARTIALLY IMPLEMENTED | 400 checks and try/catch/finally | Temp cleanup and UI messages exist. | Exception details leak; no global taxonomy, retry/backoff, timeout or overload handling. |
| Logging | PARTIALLY IMPLEMENTED | `logger.info/exception` | Logs filename/content type/size and stack traces under logger name. | Logging not configured/structured; no correlation/metrics; filenames may be sensitive metadata. |
| Authentication | NOT IMPLEMENTED | No auth middleware/routes | — | Public endpoint if exposed. |
| Database integration | NOT IMPLEMENTED | No dependency/schema/connection | — | No users, sessions, transcripts, jobs or audit state. |
| Audio persistence | NOT IMPLEMENTED | temp paths deleted in `finally` / background task | Ephemeral OS temp files only. | No retention controls or object store. |
| Testing | NOT IMPLEMENTED | No tracked test files/tooling | Manual audit checked health and simple 400 paths. | No functional/model/API/security/load tests. |
| Deployment | PARTIALLY IMPLEMENTED | `backend/Dockerfile` | Backend container uses Uvicorn on 7860. | No frontend image, Compose, CI, production config or healthcheck; model mismatch. |
| Scalability | NOT IMPLEMENTED | `_transcribe_lock` serializes work | Cache gives process-local reuse. | No admission control, queue, replica strategy, storage, metrics, or capacity test. |
| Performance optimization | PARTIALLY IMPLEMENTED | `int8` default, VAD, `beam_size=1`, cache | Practical local speed choices. | No profiling/benchmark/reproducible SLO. |
| Documentation | PARTIALLY IMPLEMENTED | three READMEs | Basic run paths and overview exist. | TTS/API contract/deployment/security docs incomplete and source drift present. |
