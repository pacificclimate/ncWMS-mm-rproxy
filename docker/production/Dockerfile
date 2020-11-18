FROM ubuntu:20.04

MAINTAINER Rod Glover <rglover@uvic.ca>

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get -yq install \
        libpq-dev \
        python3 \
        python3-dev \
        python3-pip \
        postgresql-client

ADD . /app
WORKDIR /app

RUN pip3 install -i https://pypi.pacificclimate.org/simple/ -r requirements.txt
RUN pip3 install gunicorn && \
    pip3 install gunicorn[gevent]
RUN pip3 install .

EXPOSE 8000

RUN groupadd -g 999 user \
    && useradd -r -u 999 -g user user
USER user

ENTRYPOINT ["gunicorn", "-c", "./docker/production/gunicorn.config.py", "ncwms_mm_rproxy.wsgi:app"]
