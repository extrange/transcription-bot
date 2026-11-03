# Base image for all stages. Pin the tag and digest for reproducible builds.
FROM python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913 AS base

# Install uv (pinned; Renovate keeps the digest current).
COPY --from=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 /uv /uvx /bin/

ENV APP_DIR=/app \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/home/user/.cache/uv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Make `python` resolve to the project virtualenv.
ENV PATH="/app/.venv/bin:$PATH"

# ffmpeg provides ffprobe, which is used to measure media duration. tzdata is
# required for ZoneInfo lookups (Settings.TZ defaults to Asia/Singapore).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 user \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash user \
    && mkdir -p "$APP_DIR" "$UV_CACHE_DIR" \
    && chown -R user:user "$APP_DIR" /home/user

USER user
WORKDIR $APP_DIR

#--------------------

FROM base AS deployment

# Install dependencies first so source-only changes reuse this layer.
RUN --mount=type=cache,target=$UV_CACHE_DIR,uid=1000,gid=1000 \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

COPY --chown=user:user pyproject.toml uv.lock README.md ./
COPY --chown=user:user src ./src

# Installing the project separately from its dependencies keeps caching optimal.
RUN --mount=type=cache,target=$UV_CACHE_DIR,uid=1000,gid=1000 \
    uv sync --frozen --no-dev

CMD ["python", "-m", "transcription_bot.main"]
