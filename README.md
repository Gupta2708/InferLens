<div align="center">

# InferLens

**A full-stack LLM observability platform for tracing, replaying, and comparing inference calls across providers.**

[![Next.js](https://img.shields.io/badge/Next.js-App_Router-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis Streams](https://img.shields.io/badge/Redis-Streams-DC382D?logo=redis&logoColor=white)](https://redis.io/docs/data-types/streams/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)

</div>

InferLens includes a chatbot to generate model traffic, but the main project is the infrastructure around each LLM call: provider routing, inference logging, Redis-based ingestion, PostgreSQL persistence, dashboards, trace replay, provider comparison, and PII-safe observability.

Most teams can build a chatbot before they can explain what happened inside a single LLM request. InferLens answers which provider/model handled it, how long it took, how many tokens it used, whether it streamed, failed, or was cancelled, what context was sent, whether sensitive data was redacted, and whether the request can be replayed.

---

## Features

- Multi-turn chatbot with short context window, streaming responses, and cancellation
- Provider-agnostic LLM gateway with Mock, OpenAI, and Gemini adapters
- Provider/model validation to prevent invalid combinations
- Inference logs with latency, first-token timing, tokens, cost, status, and errors
- Redis Streams ingestion pipeline with worker processing
- PostgreSQL storage for messages, traces, logs, spans, stream events, and comparisons
- PII redaction for observability previews
- Dashboard for requests, latency, errors, cancellations, tokens, cost, and provider usage
- Trace detail with spans, stream events, redactions, provider errors, and replay history
- Replay from safe request snapshots
- Provider comparison across configured models
- Docker Compose setup for local development

---

## Architecture

```mermaid
flowchart LR
    User([User]) --> Web[Next.js Web UI]
    Web --> API[FastAPI API]

    subgraph Runtime[API Runtime]
      API --> Chat[Chat Service]
      Chat --> Gateway[LLM Gateway]
      Chat --> Logger[Observability Logger]
      Logger --> Ingestion[IngestionService.enqueue]
    end

    Gateway --> Mock[Mock Provider]
    Gateway --> OpenAI[OpenAI Provider]
    Gateway --> Gemini[Gemini Provider]

    Ingestion --> Redis[(Redis Streams)]
    Redis --> Worker[Ingestion Worker]
    Worker --> Redaction[PII Redaction]
    Redaction --> DB[(PostgreSQL)]

    DB --> Dashboard[Dashboard]
    DB --> Logs[Logs & Traces]
    DB --> Replay[Replay]
    DB --> Compare[Provider Comparison]
```

The request path stays focused: **UI -> API -> gateway -> provider**. Observability data forks through the logger, gets queued in Redis, and is persisted asynchronously by the worker after redaction.

---

## Inference Flow

```mermaid
sequenceDiagram
    participant UI as Web UI
    participant API as FastAPI
    participant Chat as ChatService
    participant GW as LLMGateway
    participant Provider as Provider
    participant Log as ObservabilityLogger
    participant Redis as Redis Streams
    participant Worker as Worker
    participant DB as PostgreSQL

    UI->>API: Send chat message using streaming endpoint
    API->>Chat: Store message and load recent context
    Chat->>GW: Validate provider/model and route request
    GW->>Provider: Forward normalized LLMRequest
    Provider-->>GW: Chunks, response, or error
    GW-->>Chat: Normalized provider output
    Chat-->>UI: Stream response chunks
    Chat->>Log: Capture trace, spans, tokens, latency, snapshot
    Log->>Redis: Enqueue inference event
    Redis->>Worker: Consume stream event
    Worker->>Worker: Redact previews and normalize payload
    Worker->>DB: Persist logs, traces, spans, events, redactions
```

---

## Replay Flow

Replay rebuilds a request from `request_snapshot_json`, which contains only replay-safe inputs. API keys, auth headers, cookies, and bearer tokens are never stored there.

```mermaid
flowchart LR
    Trace[Trace Page] --> ReplayAPI[POST /api/traces/:id/replay]
    ReplayAPI --> Snapshot[Load request_snapshot_json]
    Snapshot --> Options[Apply replay options]
    Options --> Gateway[LLM Gateway]
    Gateway --> Provider[Provider]
    Provider --> Logger[Observability Logger]
    Logger --> Redis[(Redis Streams)]
    Redis --> Worker[Worker persistence]
    Worker --> Result[Replay trace and log rows]
```

---

## Provider Comparison Flow

Comparison reuses the same gateway and logging stack. Each selected provider/model target gets its own trace and log.

```mermaid
flowchart TB
    Prompt[Prompt + selected targets] --> Run[Create comparison run]
    Run --> Fanout{For each target}
    Fanout --> A[Provider/model A]
    Fanout --> B[Provider/model B]
    Fanout --> C[Provider/model C]
    A --> Results[(comparison_results)]
    B --> Results
    C --> Results
    Results --> UI[Comparison UI: latency, tokens, cost, output, errors, trace link]
```

No quality ranking, LLM-as-judge, or benchmark scoring is included.

---

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | Next.js App Router, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Pydantic, SQLAlchemy, Alembic, Uvicorn |
| Database | PostgreSQL |
| Queue | Redis Streams |
| Providers | Mock, OpenAI, Gemini |
| Local Infra | Docker Compose |

---

## Core Pages

| Page | Purpose |
| --- | --- |
| `/chat` | Generate inference traffic |
| `/dashboard` | View latency, token, cost, error, and provider metrics |
| `/logs` | Inspect inference requests |
| `/traces/[traceId]` | Debug one request lifecycle |
| `/comparisons` | Compare provider/model performance |
| `/settings/providers` | View configured provider models |

---

## Quick Start

```bash
cp .env.example .env
# PowerShell: Copy-Item .env.example .env

docker compose up --build
```

Open:

- Web: http://localhost:3000/chat
- API health: http://localhost:8000/health

Run checks:

```bash
cd apps/api && python -m pytest
corepack pnpm@9.12.3 --dir apps/web build
docker compose config
```

Do not commit `.env`.

---

## Mock Mode

Mock mode runs the full observability pipeline without real provider keys. It still creates logs, traces, dashboard metrics, replays, comparisons, stream events, and redaction records.

```env
LLM_MOCK_MODE=true
DEFAULT_PROVIDER=mock
DEFAULT_MODEL=mock-fast
```

| Model | Purpose |
| --- | --- |
| `mock-fast` | Fast successful response |
| `mock-slow` | Slow streaming response for cancellation testing |
| `mock-error` | Simulated provider error |

To use real providers, set `LLM_MOCK_MODE=false` and configure backend-only provider keys:

```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

---

## Deployment

A typical hosted deployment uses separate services for web, API, worker, Postgres, and Redis.

### Frontend

Deploy `apps/web` as a Next.js app.

```text
Root Directory: apps/web
Install Command: corepack enable && corepack pnpm@9.12.3 install --frozen-lockfile
Build Command: corepack pnpm@9.12.3 build
Output Directory: default / empty
```

Set:

```env
NEXT_PUBLIC_API_BASE_URL=https://YOUR-API-DOMAIN
```

### API

Deploy `apps/api` as a Docker Web Service.

```text
Root Directory: apps/api
Dockerfile Path: Dockerfile
Docker Build Context Directory: apps/api
Docker Command: empty
```

Set:

```env
SERVICE_ROLE=api
DATABASE_URL=postgresql+psycopg://USER:ENCODED_PASSWORD@HOST:PORT/DATABASE
REDIS_URL=rediss://default:REDIS_TOKEN@REDIS_HOST:6379
FRONTEND_URL=https://YOUR-WEB-DOMAIN
CORS_ORIGINS=https://YOUR-WEB-DOMAIN,http://localhost:3000,http://127.0.0.1:3000
LLM_MOCK_MODE=true
OPENAI_API_KEY=
GEMINI_API_KEY=
```

Use `postgresql+psycopg://` for PostgreSQL. If the database password contains special characters, URL-encode them, for example `!` as `%21`.

### Worker

Deploy `apps/api` a second time as a Docker Web Service for ingestion processing.

```text
Root Directory: apps/api
Dockerfile Path: Dockerfile
Docker Build Context Directory: apps/api
Docker Command: empty
```

Set:

```env
SERVICE_ROLE=worker-web
DATABASE_URL=postgresql+psycopg://USER:ENCODED_PASSWORD@HOST:PORT/DATABASE
REDIS_URL=rediss://default:REDIS_TOKEN@REDIS_HOST:6379
LLM_MOCK_MODE=false
LOG_LEVEL=INFO
```

`SERVICE_ROLE=worker-web` starts a small health server and the Redis ingestion loop together. The health URL should return:

```json
{"status":"ok","worker":"running"}
```

Use the Redis TCP URL (`redis://` or `rediss://`), not a REST URL.

### Deployment Checklist

- API health returns `{"status":"ok"}`.
- Provider configs load from `/api/providers`.
- Worker health returns `{"status":"ok","worker":"running"}`.
- Frontend loads `/chat`.
- Sending a `mock / mock-fast` message creates a log row.
- Dashboard request count updates.
- A log row opens a trace page.

---

## Security and Reliability

- PII redaction covers emails, phone numbers, API-key-like strings, JWT-like tokens, and credit-card-like patterns in observability previews
- API keys are never stored in request snapshots
- Headers, cookies, bearer tokens, and secrets are not persisted as raw metadata
- Provider error messages are sanitized before display
- Canonical chat content is kept separate from redacted observability previews
- Failures are normalized in traces: invalid provider/model, missing key, rate limit, model not found, server error, invalid request, cancellation, and worker persistence failure
- Ingestion is idempotent by `event_id`; repeated worker failures move to dead-letter storage

---

## License

MIT
