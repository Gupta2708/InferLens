from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.seed import seed_provider_configs
from app.db.session import engine
from app.llm.gateway import LLMGateway
from app.observability.metrics import CONTENT_TYPE_LATEST, generate_latest
from app.observability.telemetry import configure_telemetry, shutdown_telemetry
from app.observability.logging import configure_logging
from redis import Redis
from app.routes import comparisons, conversations, dashboard, ingest, logs, providers, traces

settings = get_settings()


def _cors_origins() -> list[str]:
    configured = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    defaults = [settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"]
    return sorted({origin.rstrip("/") for origin in [*configured, *defaults] if origin})


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    seed_provider_configs()
    configure_telemetry("inferlens-api")
    yield
    shutdown_telemetry()


app = FastAPI(title="InferLens API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations.router)
app.include_router(providers.router)
app.include_router(ingest.router)
app.include_router(logs.router)
app.include_router(dashboard.router)
app.include_router(traces.router)
app.include_router(comparisons.router)


@app.get("/health")
def health(): return {"status": "ok"}


@app.get("/health/live")
def health_live(): return {"status": "ok", "service": "inferlens-api"}


@app.get("/health/ready")
async def health_ready():
    checks = {"database": False, "redis": False, "provider_registry": False}
    try:
        with engine.connect() as connection: connection.exec_driver_sql("SELECT 1")
        checks["database"] = True
    except Exception: pass
    try:
        Redis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2).ping(); checks["redis"] = True
    except Exception: pass
    try:
        checks["provider_registry"] = bool(LLMGateway().providers)
    except Exception: pass
    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}


@app.get("/metrics")
def metrics(): return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
