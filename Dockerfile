FROM python:3.11-slim

# System deps some ML wheels need at build/runtime (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so this layer caches across code-only changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code (includes app/static/index.html and, if present, app/adapter/)
COPY app ./app

# If you commit adapter weights locally instead of using a HF Hub repo id,
# they'll already be under app/ above. Otherwise ADAPTER_PATH at runtime
# should be a HF Hub repo id and huggingface_hub will download it on warm-up.

ENV PYTHONUNBUFFERED=1 \
    GLINER_BASE_MODEL=fastino/gliner2-base-v1 \
    ADAPTER_PATH=adapter/best \
    NER_LABELS=PERSON,GPE,ORG,EVENT,DATE \
    NER_THRESHOLD=0.3 \
    MAX_TEXT_LEN=4000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
