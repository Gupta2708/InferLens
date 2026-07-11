from threading import Thread

from fastapi import FastAPI

from app.workers.ingestion_worker import run_forever

app = FastAPI(title="InferLens Worker", version="0.1.0")
_worker_thread: Thread | None = None


def _start_worker_once() -> None:
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _worker_thread = Thread(target=run_forever, name="ingestion-worker", daemon=True)
    _worker_thread.start()


@app.on_event("startup")
def startup() -> None:
    _start_worker_once()


@app.get("/health")
def health() -> dict[str, str]:
    if _worker_thread and _worker_thread.is_alive():
        return {"status": "ok", "worker": "running"}
    return {"status": "starting", "worker": "not_running"}
