FROM ubuntu:24.04 AS builder

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get -yq install \
    build-essential \
    libpq-dev \
    pipx \
    python3 \
    python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PATH="/root/.local/bin:$PATH"

RUN pipx install poetry

COPY pyproject.toml poetry.lock README.md ./
COPY ncwms_mm_rproxy ./ncwms_mm_rproxy
COPY docker/production ./docker/production

RUN poetry config virtualenvs.in-project true && \
    poetry install --only main

FROM ubuntu:24.04

LABEL maintainer="PCIC DevOps <pcic.devops@uvic.ca>"

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get -yq install \
    curl \
    libpq5 \
    python3 \
    postgresql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/readyz || exit 1

RUN groupadd -g 999 user \
    && useradd -r -u 999 -g user user
USER user

ENTRYPOINT ["gunicorn", "-c", "./docker/production/gunicorn.config.py", "ncwms_mm_rproxy.wsgi:app"]
