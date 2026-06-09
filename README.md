<div align="center">

# 🔭 InferLens

**A full-stack LLM observability platform** — trace, replay, and compare inference calls across providers.

[![Next.js](https://img.shields.io/badge/Next.js-App_Router-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis_Streams-DC382D?logo=redis&logoColor=white)](https://redis.io/docs/data-types/streams/)
[![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)

</div>

There's a chatbot to generate model traffic, but the core project is the infrastructure around it: gateway routing, inference logging, Redis-based ingestion, Postgres persistence, dashboards, trace replay, provider comparison, and PII-safe observability.

> **Most teams can build a chatbot before they can explain what happened inside a single LLM call.** InferLens answers: which provider/model handled it, how long it took, how many tokens it used, whether it streamed/failed/cancelled, what context was sent, whether sensitive data was redacted, whether it can be replayed, and how providers compare on latency, cost, and failures.

---

## ✨ Features

- Multi-turn chatbot with short context window, streaming (`fetch()` + `ReadableStream`), and mid-generation cancel
- Provider-agnostic LLM gateway with **Mock / OpenAI / Gemini** adapters and provider/model validation
- Inference logs with latency, tokens, cost, status, and errors
- Redis Streams ingestion + background worker with retry / dead-letter handling
- PostgreSQL storage for messages, traces, logs, spans, stream events, and comparisons
- PII redaction for observability previews
- Dashboard (requests, latency, errors, cancellations, tokens, cost, provider usage)
- Trace detail with spans, stream events, redactions, provider errors, and replay history
- Replay from safe request snapshots + provider comparison across configured models
- One-command Docker Compose setup

---

## 🏗️ Architecture

```mermaid
flowchart LR
    User([User]) --> Web[Next.js Web UI]

    subgraph CLIENT[" "]
      Web
    end

    Web --> API[FastAPI API]

    subgraph RUNTIME["API Runtime"]
      API --> Chat[Chat Service]
      Chat --> Gateway[LLM Gateway]
      Chat --> Logger[Observability Logger]
      Logger --> Ingestion[IngestionService.enqueue]
    end

    Gateway --> Mock[Mock Provider]
    Gateway --> OpenAI[OpenAI Provider]
    Gateway --> Gemini[Gemini Provider]

    Ingestion --> Redis[(Redis Streams)]

    subgraph PIPE["Ingestion Pipeline"]
      Redis --> Worker[Ingestion Worker]
      Worker --> Redaction[PII Redaction]
    end

    Redaction --> DB[(PostgreSQL)]

    subgraph READ["Read Surfaces"]
      Dashboard[Dashboard]
      Logs[Logs & Traces]
      Replay[Replay]
      Compare[Provider Comparison]
    end

    DB --> Dashboard
    DB --> Logs
    DB --> Replay
    DB --> Compare

    classDef store fill:#fde68a,stroke:#b45309,color:#1f2937;
    classDef provider fill:#bfdbfe,stroke:#1d4ed8,color:#1f2937;
    classDef read fill:#bbf7d0,stroke:#15803d,color:#1f2937;
    class Redis,DB store;
    class Mock,OpenAI,Gemini provider;
    class Dashboard,Logs,Replay,Compare read;
```

The request path stays simple: **UI → API → gateway → provider**. Everything observable forks off through the **Observability Logger**, gets enqueued to Redis, and is persisted asynchronously by the worker (after redaction) so logging never blocks the user's response.

---

## 🔁 Inference Flow

End-to-end path of a single chat message, from keystroke to persisted trace:

```mermaid
sequenceDiagram
    participant UI as Web UI
    participant API as FastAPI
    participant Chat as ChatService
    participant GW as LLMGateway
    participant Prov as Provider
    participant Log as ObservabilityLogger
    participant Redis as Redis Streams
    participant Worker as Worker
    participant DB as PostgreSQL

    UI->>API: Send chat message (stream)
    API->>Chat: Store message + load recent context
    Chat->>GW: Validate provider/model + route
    GW->>Prov: Forward normalized LLMRequest
    Prov-->>GW: Chunks / response / error
    GW-->>Chat: Stream chunks back

    par Stream to user
        Chat-->>API: Incremental tokens
        API-->>UI: Streamed response + final status
    and Observe in background
        Chat->>Log: Capture trace, spans, tokens, latency, snapshot
        Log->>Redis: XADD inference event
        Redis->>Worker: XREADGROUP
        Worker->>Worker: Redact previews + normalize payload
        Worker->>DB: Persist logs, traces, spans, events, redactions
    end
```

---

## ▶️ Replay Flow

Replay rebuilds a request from `request_snapshot_json` — which holds only **replay-safe** inputs. Secrets, auth headers, and raw API keys are never stored there.

```mermaid
flowchart LR
    T[Trace Page] -->|POST /api/traces/:id/replay| RS[ReplayService]
    RS --> SNAP[Load request_snapshot_json]
    SNAP --> MUT[Apply replay options]
    MUT --> GEN[ChatService.generate_once]
    GEN --> GW[LLM Gateway] --> P[Provider]
    P --> LOG[Observability Logger] --> Q[Ingestion]
    Q --> WK[Worker persistence]
    WK --> NEW[New trace + log rows]
    NEW --> T2[Replay result in trace UI]

    classDef safe fill:#bbf7d0,stroke:#15803d,color:#1f2937;
    class SNAP,NEW safe;
```

---

## ⚖️ Provider Comparison Flow

Comparison reuses the same gateway and logging stack — no separate evaluation engine. Each target gets **its own trace and log**.

```mermaid
flowchart TB
    P[Prompt + selected targets] --> RUN[Create comparison_run]
    RUN --> FAN{For each target}
    FAN --> G1[generate_once → Provider A]
    FAN --> G2[generate_once → Provider B]
    FAN --> G3[generate_once → Provider C]
    G1 --> R[(comparison_results)]
    G2 --> R
    G3 --> R
    R --> UI[Comparison page: latency · tokens · cost · output · errors · trace link]
```

> No quality ranking, LLM-as-judge, or benchmark scoring is included.

---

## 🧰 Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js (App Router), TypeScript, Tailwind CSS, Recharts |
| **Backend** | FastAPI, Pydantic, SQLAlchemy, Alembic, Uvicorn |
| **Infra** | PostgreSQL, Redis Streams, Docker Compose |
| **Providers** | Mock, OpenAI, Gemini |

---

## 🖥️ Core Pages

| Page | Purpose |
|---|---|
| `/chat` | Generate inference traffic |
| `/dashboard` | Aggregate latency, token, cost, error, and provider metrics |
| `/logs` | Inspect every inference request |
| `/traces/[traceId]` | Debug one request lifecycle |
| `/comparisons` | Compare provider/model performance |
| `/settings/providers` | View configured provider models |

---

## 🚀 Quick Start

```bash
cp .env.example .env          # PowerShell: Copy-Item .env.example .env
docker compose up --build
```

Open:

- **Web:** http://localhost:3000/chat
- **API health:** http://localhost:8000/health

Compose starts `web`, `api`, `worker`, `postgres`, and `redis`. Don't commit `.env`.

---

## 🧪 Mock Mode

Runs the **entire pipeline without real keys** — still creates logs, traces, dashboard metrics, replays, comparisons, stream events, and redaction records.

```env
LLM_MOCK_MODE=true
DEFAULT_PROVIDER=mock
DEFAULT_MODEL=mock-fast
```

| Model | Purpose |
|---|---|
| `mock-fast` | Fast successful response |
| `mock-slow` | Slow streaming response (cancellation testing) |
| `mock-error` | Simulated provider error |

To use real providers, add `OPENAI_API_KEY` / `GEMINI_API_KEY` to root `.env`, set `LLM_MOCK_MODE=false`, and pick the provider in the UI. Keys are backend-only and never exposed to the frontend.

---

## 🔒 Security & Reliability

- PII redaction (emails, phone numbers, API-key-like strings, JWT-like tokens, credit-card-like patterns) on observability previews
- API keys never stored in request snapshots; headers, cookies, and bearer tokens never persisted
- Provider error messages sanitized before display; canonical chat content kept separate from redacted previews
- Failures normalized and visible in traces: invalid provider/model, missing key, rate limit, model not found, server error, invalid request, cancellation, worker persistence failure
- Ingestion is idempotent by `event_id`; repeated worker failures move to dead-letter storage

---

<div align="center">
<sub>MIT Licensed</sub>
</div>