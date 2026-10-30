FROM ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv

FROM python:3.15-slim AS base

# Inherited by all stages
ENV APP_DIR=/app
ENV TZ=Asia/Singapore


SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# uv is used to install and manage dependencies
COPY --from=uv /uv /bin/uv

#-------------------

FROM base AS builder

# uv fetches the `python-utils` git dependency, which needs git
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git && \
    rm -rf /var/lib/apt/lists/*

# These variables will apply to the descendant stage (test) as well

# uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=$APP_DIR/.venv

ENV PATH="$APP_DIR/.venv/bin:$PATH" \
    PYTHONPATH=$APP_DIR/src \
    VIRTUAL_ENV=$APP_DIR/.venv

WORKDIR $APP_DIR

COPY uv.lock pyproject.toml ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

#--------------------

# Inherits ENV from builder
FROM builder AS test

# Install dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

WORKDIR $APP_DIR

COPY . $APP_DIR

# In the venv created by uv, from PATH
RUN pyright && pytest

#--------------------

FROM base AS deployment

ENV PATH="$APP_DIR/.venv/bin:$PATH" \
    PYTHONPATH=$APP_DIR/src \
    VIRTUAL_ENV=$APP_DIR/.venv

RUN useradd -ms /bin/bash --user-group -u 1000 user

USER user

# Copy virtual environment from builder
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY . $APP_DIR

# Change as necessary
CMD ["python", "-m", "transcription_bot.main"]
