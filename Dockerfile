# syntax=docker/dockerfile:1.7

ARG PYTHON_BASE_IMAGE=python:3.13.15-slim-trixie@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285

FROM ${PYTHON_BASE_IMAGE} AS api

LABEL org.opencontainers.image.title="EvalGate API"
LABEL org.opencontainers.image.description="Governed RAG evaluation API release-candidate runtime"
LABEL org.opencontainers.image.version="0.10.0"
LABEL org.opencontainers.image.source="https://example.invalid/evalgate-local-only"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_NO_PROGRESS=1
ENV PATH="/app/apps/api/.venv/bin:${PATH}"

WORKDIR /app

RUN groupadd --system --gid 10001 evalgate \
    && useradd --system --uid 10001 --gid evalgate --home-dir /app --shell /usr/sbin/nologin evalgate

COPY --chown=10001:10001 apps/api/pyproject.toml apps/api/uv.lock apps/api/README.md /app/apps/api/
COPY --chown=10001:10001 apps/api/src /app/apps/api/src
COPY --chown=10001:10001 apps/api/migrations /app/apps/api/migrations
COPY --chown=10001:10001 contracts /app/contracts
COPY --chown=10001:10001 data /app/data

RUN python -m pip install --no-cache-dir uv==0.12.3 \
    && uv sync --project apps/api --locked --no-dev --no-editable

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).read()" || exit 1

CMD ["evalgate-api"]
