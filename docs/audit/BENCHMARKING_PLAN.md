# Testing and Benchmarking Plan

## Principles

Do not publish a single “accuracy” or “low latency” number. Version the dataset, model, `faster-whisper` configuration, container image/revision, hardware, concurrency, audio format and scoring script for each run. Keep audio only with consent/licence; store identifiers and checksums rather than private content in reports.

## Test layers

| Layer | What to test | Method / acceptance |
|---|---|---|
| Unit | settings parsing, allowed language/voice, hallucination guard, transcript merge/order, error mapping | Pytest, parameterized unit tests. No model required. |
| API contract | status codes, multipart validation, body limits, response schemas, readiness, provider/model failures | FastAPI `TestClient` with mocked STT/TTS adapters. |
| Audio pipeline | accepted/rejected container/codecs, corrupt/truncated file, duration limit, mono/stereo/rates, quiet/noisy samples | Small licensed fixtures plus an isolated decoder/probe test. |
| Browser | permissions denied, record/stop, out-of-order responses, retry/cancel, TTS stop | Playwright/Cypress with mocked API and one manual supported-browser matrix. |
| Integration | actual model result contract and temp-file lifecycle | Run a small fixed set in Docker; assert no retained temp artifact after response. |
| Load/recovery | concurrent requests, queue saturation, disconnects, model/TTS temporary failure | k6/Locust; assert bounded 429/503 behavior and eventual cleanup. |

## Evaluation corpus design

Create a versioned manifest with audio checksum, licence/consent, language, dialect/region if consented, script, sample rate, duration, noise condition, code-mix tag, reference transcript and split. Start modestly: held-out English, Hindi, Telugu, Marathi and Tamil utterances, plus English-Hindi and English-Telugu code-switch sets. Ensure train/tuning and final test speakers do not overlap. Do not tune VAD/model prompts/thresholds on the held-out test split.

Define text normalization before scoring (Unicode normalization, whitespace, punctuation, numeral/script policy); publish it. Report both raw and normalized results where script/language conventions make normalization consequential.

## Metrics and formulas

| Metric | Definition | Report breakdown |
|---|---|---|
| WER | `(substitutions + deletions + insertions) / reference words` | Overall and by language, noise, duration, code-mix, model/config. |
| CER | `(S + D + I) / reference characters` | Essential for Indian scripts and mixed-script output. |
| RTF | transcription processing time / audio duration | p50/p95 plus CPU/GPU model profile. Below 1 is faster than audio duration, but do not set an SLO before measuring. |
| E2E latency | browser final audio availability to response/first partial/final UI event | p50/p95/p99 separately; include upload and queue time. |
| Throughput | completed audio seconds or requests per wall-clock second | State concurrency, audio length, hardware and rejection rate. |
| Resource use | peak/average RSS, CPU, GPU memory/utilization, temp disk | Per worker/process and whole host. |
| Reliability | success rate, timeout rate, 4xx/5xx split, cleanup failures | By endpoint/load profile. |
| Translation | human adequacy/fluency rubric and/or suitable automatic metric | Per language pair on held-out references; do not compare incompatible metrics. |
| TTS | human intelligibility/naturalness MOS-style study or carefully controlled preference test | Disclose sample size/listeners/voice/provider; never invent MOS. |

## Reproducible experiment procedure

1. Freeze the Git SHA, lock dependencies, record Docker image digest, model identifier/cache revision, environment variables excluding secrets, and hardware/OS.
2. Validate the manifest: checksums, no missing references, language/split counts, and duration distribution.
3. Run a warm-up set separately and exclude it from timed scoring; record cold-start time as a separate metric.
4. Run deterministic offline STT scoring at concurrency 1 for each configuration. Save raw JSON responses and normalized score outputs.
5. Run service E2E tests at fixed audio durations and concurrency levels (for example 1, then increasing levels) until the specified saturation/error threshold. Record client and server timestamps.
6. Repeat each timed scenario at least three times, report medians/ranges, and retain commands/configuration in a results directory.
7. Inspect errors and qualitative examples by stratum. Do not use test examples to change a model or threshold; put improvements through the tuning split then rerun held-out scoring.
8. Produce a concise report answering: which configuration is selected, which languages/conditions remain weak, what hardware/cost it needs, and what user-visible latency it provides.

## Current-baseline note

The repository has no tracked corpus, scoring code, test fixtures, performance logs, model revision record, or measured WER/CER/RTF. Therefore this audit intentionally makes no accuracy, latency, throughput, translation-quality or TTS-quality claim.
