# Use this for Render "Docker" web services (repo root: Dockerfile + context .).
# Do NOT use native "Python" runtime with pip — Render may use Python 3.14 and pydantic-core
# will try to compile Rust and fail. This image pins Python 3.12.
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
