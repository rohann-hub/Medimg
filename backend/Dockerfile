# Build context is the repo root (see docker-compose.yml) so the shared ml/medai package can be copied in.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv

# CPU-only PyTorch keeps the image ~1.5 GB instead of ~6 GB. For a GPU host, use an
# nvidia/cuda base image and the default PyPI torch wheels instead.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY ml/ ml/
RUN pip install ./ml

COPY backend/ backend/
WORKDIR /srv/backend

RUN useradd --create-home appuser && mkdir -p /srv/backend/var && chown -R appuser /srv/backend/var
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
