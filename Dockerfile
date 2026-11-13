# Base image for all stages. Pin the tag and digest for reproducible builds.
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS base

# Install uv (pinned; Renovate keeps the digest current).
COPY --from=ghcr.io/astral-sh/uv:0.13.8@sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85 /uv /uvx /bin/

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
