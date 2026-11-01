FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WHISPER_MODEL_SIZE=small \
    WHISPER_DEVICE=cpu \
    WHISPER_COMPUTE_TYPE=int8 \
    TEMP_DIRECTORY=/tmp/pelocal-speech-api \
    HF_HOME=/opt/model-cache \
    HF_HUB_CACHE=/opt/model-cache/hub \
    XDG_CACHE_HOME=/opt/model-cache

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /tmp/pelocal-speech-api \
    && mkdir -p /opt/model-cache \
    && chown -R appuser:appuser /app /tmp/pelocal-speech-api /opt/model-cache
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
