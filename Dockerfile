FROM python:3.12-slim AS base

# Inherited by all stages
ENV POETRY_VERSION=1.8.3
ENV APP_DIR=/app
ENV TZ=Asia/Singapore


SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl=7.88.1-10+deb12u6 \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*

#-------------------

FROM base AS dev

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    sqlite3

# trufflehog: secret scanning
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin

# Poetry & dependencies are installed in the devcontainer via postCreateCommand

#-------------------

FROM base AS builder

RUN pip install --no-cache-dir poetry=="$POETRY_VERSION"

# These variables will apply to the descendant stage (test) as well

# Poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

ENV PATH="$APP_DIR/.venv/bin:$PATH" \
    PYTHONPATH=$APP_DIR/src \
    VIRTUAL_ENV=$APP_DIR/.venv

WORKDIR $APP_DIR

COPY poetry.lock pyproject.toml ./

RUN --mount=type=cache,target=${POETRY_CACHE_DIR} \
    poetry install --without=dev --no-root

#--------------------

# Inherits ENV from builder
FROM builder AS test

# Install dev dependencies
RUN --mount=type=cache,target=${POETRY_CACHE_DIR} \
    poetry install --no-root

WORKDIR $APP_DIR

COPY . $APP_DIR

# In the venv created by poetry, from PATH
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
