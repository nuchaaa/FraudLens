FROM ghcr.io/astral-sh/uv:0.12.17 AS uv
FROM python:3.13-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock README.md ./
COPY backend ./backend
COPY infra ./infra
COPY alembic.ini ./
RUN uv sync --locked --no-dev && useradd --create-home --uid 10001 fraudlens
USER fraudlens
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]
