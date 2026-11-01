# Inference concurrency

Transcription uses two separate process-local safeguards:

- **Admission control** limits how many requests may enter the transcription
  workflow. The default is two admitted requests. A request that arrives when
  the limit is reached receives HTTP `503` with error code `SERVICE_BUSY`
  instead of waiting indefinitely.
- **Inference locking** remains inside the speech-recognition service and
  serializes calls to the shared Whisper model. This is intentionally retained
  because concurrent calls are not assumed to be safe for the configured model.

Configure admission capacity with:

```text
MAX_ADMITTED_INFERENCE_REQUESTS=2
```

The setting must be a positive integer. This is process-local capacity; it is
not shared across multiple Uvicorn workers or machines. Increasing it allows
more requests into the workflow but does not make model execution concurrent,
because the existing inference lock still serializes execution. There is no
queue or admission wait timeout in this phase: callers should retry a
`SERVICE_BUSY` response with appropriate backoff.
