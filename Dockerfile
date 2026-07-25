# syntax=docker/dockerfile:1

# --- Stage 1: build the React SPA -------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json* ./
RUN npm ci || npm install
COPY web/ ./
RUN npm run build   # -> /web/dist

# --- Stage 2: the Python app ------------------------------------------------
FROM python:3.13-slim AS app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first (cached until the lock changes).
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --extra app

# App source + card data + the built frontend.
COPY red_rising/ ./red_rising/
COPY --from=web /web/dist ./web/dist
RUN uv sync --frozen --extra app

# SQLite lives on a mounted volume so games survive redeploys.
ENV RR_DB=/data/red_rising.db RR_WEB_DIST=/app/web/dist
VOLUME /data
EXPOSE 8000

CMD ["uv", "run", "--extra", "app", "uvicorn", "red_rising.app.server:app", \
     "--host", "0.0.0.0", "--port", "8000"]
