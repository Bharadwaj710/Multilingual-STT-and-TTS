# Upgrade Roadmap and Career Prioritization

Effort estimates are engineering days for one developer familiar with the repository; they include implementation, tests and documentation, but not prolonged data annotation or cloud-account lead time.

## Upgrade catalogue by difficulty

| Upgrade | Difficulty | Prerequisites | Expected impact | Estimated effort | Files/modules affected |
|---|---|---|---|---:|---|
| Typed settings, configuration parity, README/API corrections | Level 1 — Easy | Decide supported defaults | Eliminates Docker/runtime/documentation drift | 1–2 days | config, download script, Dockerfile, READMEs |
| Upload limits, codec/language/voice validation, stable errors | Level 1 — Easy | Accepted format and product limits | Security/reliability baseline | 2–3 days | main, config, client errors/tests |
| Structured logging, request IDs, liveness/readiness | Level 1 — Easy | Logging destination | Debuggable production behavior | 2–3 days | main/config/tests/deployment docs |
| Unit/API tests and CI | Level 1 — Easy | Tiny licensed fixtures/mock adapters | Prevents regressions; interview evidence | 3–5 days | new tests, GitHub Actions, requirements |
| Ordered chunks and boundary-aware transcript assembly | Level 2 — Intermediate | Sequence protocol, test recordings | Correct continuous transcript UX | 3–5 days | App, API schema, tests |
| Benchmark/evaluation harness | Level 2 — Intermediate | Consent/licensing + transcripts | Objective WER/CER/RTF results | 4–7 days | new evaluation package, dataset manifest, docs |
| Translation adapter with evaluation | Level 2 — Intermediate | Target language pairs/quality criteria | Explicit multilingual workflow | 4–8 days | new adapter/routes/UI/tests |
| Hardened TTS adapter and voice routing | Level 2 — Intermediate | Provider policy, text limits, privacy stance | Reliable STT-to-speech experience | 3–5 days | main/services/config/UI/tests |
| Audio normalization/probe and VAD tuning | Level 2 — Intermediate | Tooling/container policy + corpus | Safer/more consistent input | 4–7 days | audio service/Docker/tests/benchmarks |
| PostgreSQL transcript/job metadata | Level 2 — Intermediate | Data model and retention policy | Durable user/session history | 4–6 days | models/migrations/repos/API/auth |
| WebSocket partial/final transcription | Level 3 — Advanced | Ordered event protocol, cancellation/backpressure design | Genuine interactive latency work | 8–14 days | client, API, inference gateway, tests/load tests |
| Bounded async inference and Redis worker path | Level 3 — Advanced | Job state model + observability | Reliable offline/bulk requests | 7–12 days | queue/worker/API/DB/Compose/tests |
| GPU profiling, model selection and quantization policy | Level 3 — Advanced | Target hardware + corpus | Defensible performance/quality trade-offs | 5–10 days | inference config/benchmarks/Docker/docs |
| Multi-model routing/code-switch strategy | Level 3 — Advanced | Language-labelled corpus and baseline metrics | Potential quality gain where measured | 10–18 days | LID/routing/evaluation/inference services |
| Distributed multi-replica inference and fault-tolerant streaming | Level 4 — Expert | Load SLOs, tracing, storage, queue, cloud ops | Demonstrates systems engineering at scale | 15–30+ days | platform-wide |
| Adaptive model routing and large-scale multilingual evaluation | Level 4 — Expert | Significant labelled data, monitoring, production traffic | Research/infrastructure depth | 20–40+ days | platform-wide/eval infrastructure |

## Highest-value interview upgrades

| Upgrade | AI Engineering Value | Backend Engineering Value | Resume Impact | Priority |
|---|---|---|---|---|
| Reproducible multilingual benchmark (WER/CER/RTF, documented trade-offs) | High | Medium | High | P0 |
| Input validation, resource controls, typed contracts, security posture | Medium | High | High | P0 |
| Automated API/audio tests and CI | Medium | High | High | P0 |
| Ordered chunk assembly with clear partial/final semantics | High | High | High | P1 |
| Structured metrics/logging plus Docker/Compose production profile | Medium | High | High | P1 |
| Translation/TTS behind provider interfaces with evaluation | High | High | High | P1 |
| WebSocket streaming with load/backpressure tests | High | High | High | P2 |
| PostgreSQL jobs/history and object-storage lifecycle | Medium | High | Medium–High | P2 |

The first six are the strongest 5–8 upgrades for an entry-level AI Backend Engineer portfolio because each can be demonstrated with architecture decisions, test artifacts, measured results, and known trade-offs—not just another UI feature.

## Phased implementation plan

### Phase 0 — Existing project stabilization (4–6 days, essential)

**Objectives:** make current behavior reproducible and safe enough to assess.
**Features:** unify model defaults across config/Docker/download; request/response schemas; size/type/language/voice validation; generic error responses; structured logs; correct docs; basic Docker health/readiness.
**Prerequisites/dependencies:** decide supported audio codecs, max duration/size, model default, and whether Edge TTS is acceptable for demo data.
**Deliverables:** configuration matrix, OpenAPI examples, hardened routes, smoke tests.
**Acceptance criteria:** container startup uses the declared model only; invalid/oversize inputs fail predictably; readiness distinguishes loaded/unloaded model; no secret/raw exception is returned.

### Phase 1 — Essential engineering improvements (6–10 days, essential)

**Objectives:** establish regression safety and transcript correctness.
**Features:** unit/API tests, test fixtures, CI, sequence IDs and ordered client commits, boundary strategy, request IDs/metrics, local Compose profile.
**Dependencies:** Phase 0 stable contracts.
**Deliverables:** passing CI, test report, endpoint contract, latency/error dashboards or local metrics scrape.
**Acceptance criteria:** delayed/out-of-order mock responses never reorder transcript; tests cover invalid media, model/provider error and temp cleanup; documented local one-command stack.

### Phase 2 — Core multilingual STT-to-TTS functionality (8–15 days, essential only if product requires it)

**Objectives:** provide an explicit, evaluated multilingual workflow.
**Features:** audio probe/normalization, defined LID policy, translation adapter for named source/target pairs, TTS provider abstraction/voice routing, transcript metadata model only if history is required.
**Dependencies:** labelled evaluation samples and privacy/provider decisions.
**Deliverables:** supported-language matrix, end-to-end tests and quality report.
**Acceptance criteria:** source language, target language and selected voice are observable in a job/result; unsupported combinations fail cleanly; baseline versus upgraded results are published.

### Phase 3 — Advanced AI/backend engineering (12–22 days, optional advanced)

**Objectives:** lower interactive latency or support longer/offline work.
**Features:** WebSocket partial/final protocol *or* Redis-backed asynchronous jobs (choose the user need first), cancellation/backpressure, durable job state, GPU/model profile.
**Dependencies:** Phases 0–2 metrics, capacity target and a load test.
**Deliverables:** protocol spec, load test results, operational limits.
**Acceptance criteria:** defined concurrent-load behavior has bounded queueing; client reconnect/cancel semantics are tested; no loss or reordering of final transcripts.

### Phase 4 — Performance and evaluation (7–12 days, essential for strong technical claims)

**Objectives:** choose models/configuration from evidence.
**Features:** WER/CER/RTF suite, memory/CPU/GPU instrumentation, concurrency tests, error taxonomy, candidate-model comparison, code-switch subset evaluation.
**Dependencies:** curated held-out corpus and fixed benchmark machine/container.
**Deliverables:** versioned benchmark report and configuration recommendation.
**Acceptance criteria:** every published metric links to data split, model revision/config, hardware, command and raw result artifact.

### Phase 5 — Deployment and production readiness (7–15 days, optional for public release)

**Objectives:** safely demonstrate delivery.
**Features:** Docker/Compose, CI/CD, TLS-capable ingress, secrets configuration, auth/rate limit, object storage lifecycle when retaining data, monitoring/alerts, backup/retention documentation.
**Dependencies:** clear data policy, cloud budget, expected traffic/SLO.
**Deliverables:** deployment runbook, threat model, cost/capacity notes and rollback path.
**Acceptance criteria:** fresh environment deploy is automated; health/readiness/metrics work; retention/deletion and overload behaviors are tested.

### Recommended MVP cut

Finish Phases 0, 1, and the evaluation portion of Phase 4 first. That yields a credible, measurable multilingual STT project. Add Phase 2 only for a real STT→translation→TTS user flow; add Phase 3/5 only when you can state an interactive or public-deployment requirement.
