FROM ubuntu:24.04

LABEL maintainer="Rod Glover <rglover@uvic.ca>"

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get -yq install \
    curl \
    libpq-dev \
    python3 \
    python3-dev \
    python3-pip \
    postgresql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN curl -sSL https://install.python-poetry.org | python3

COPY . .

RUN poetry config virtualenvs.in-project true && \
    poetry lock && \
    poetry install

EXPOSE 8000

RUN groupadd -g 999 user \
    && useradd -r -u 999 -g user user
USER user

ENTRYPOINT ["poetry", "run", "gunicorn", "-c", "./docker/production/gunicorn.config.py", "ncwms_mm_rproxy.wsgi:app"]
