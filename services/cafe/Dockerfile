# Build from repository root: docker compose build (context ..)
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --only-group cafe-api --link-mode=copy

COPY services/cafe/*.py ./

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
