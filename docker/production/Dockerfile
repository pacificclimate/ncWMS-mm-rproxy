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
RUN pip3 install gunicorn
RUN pip3 install .

EXPOSE 8000

ENTRYPOINT ["gunicorn", "-b", ":8000", "modelmeta2ncWMS.wsgi:app"]
