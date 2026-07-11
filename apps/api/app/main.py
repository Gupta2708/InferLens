from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.seed import seed_provider_configs
from app.routes import comparisons, conversations, dashboard, ingest, logs, providers, traces

settings = get_settings()


def _cors_origins() -> list[str]:
    configured = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    defaults = [settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"]
    return sorted({origin.rstrip("/") for origin in [*configured, *defaults] if origin})


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_provider_configs()
    yield


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
def health():
    return {"status": "ok"}