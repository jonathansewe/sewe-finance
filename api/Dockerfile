# API image: Python 3.12 + uv. Used by docker-compose locally and by Render.
FROM python:3.12-slim

# uv installs dependencies from uv.lock exactly (reproducible builds).
RUN pip install --no-cache-dir uv==0.11.32

WORKDIR /srv/api
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/srv/api/.venv/bin:$PATH"

# Dependencies first, so code edits don't re-install packages (layer cache).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# Run as a non-root user: a bug in the app can't modify the image.
RUN useradd --create-home sewe
USER sewe

EXPOSE 8000
# Apply migrations, then serve. Render runs the same command.
# --proxy-headers: take the client IP from X-Forwarded-For, but only when the
# peer is listed in FORWARDED_ALLOW_IPS (uvicorn reads that env var). D-36.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
