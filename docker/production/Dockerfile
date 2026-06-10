FROM ubuntu:24.04

LABEL maintainer="Rod Glover <rglover@uvic.ca>"

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get -yq install \
    build-essential \
    curl \
    libpq-dev \
    pipx \
    python3 \
    python3-dev \
    python3-pip \
    postgresql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PATH="/root/.local/bin:$PATH"

RUN pipx install poetry

COPY . .

RUN poetry config virtualenvs.in-project true && \
    poetry install

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/readyz || exit 1

RUN groupadd -g 999 user \
    && useradd -r -u 999 -g user user
USER user

ENTRYPOINT ["poetry", "run", "gunicorn", "-c", "./docker/production/gunicorn.config.py", "ncwms_mm_rproxy.wsgi:app"]
