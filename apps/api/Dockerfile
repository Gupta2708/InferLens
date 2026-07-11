FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV SERVICE_ROLE=api

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY app ./app

EXPOSE 8000
CMD sh -c "alembic upgrade head && if [ \"${SERVICE_ROLE:-api}\" = \"worker-web\" ]; then uvicorn app.workers.web_worker:app --host 0.0.0.0 --port ${PORT:-8000}; else uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}; fi"
