FROM python:3

ENV PYTHONBUFFERED 1
ENV APPLICATION_ROOT /app/

RUN mkdir -p $APPLICATION_ROOT

RUN set -x && apt-get update && apt-get -y install \
    locales \
    # lxml
    libxslt1-dev \
    libxml2-dev \
    lib32z1-dev \
    # psycopg2
    libpq-dev \
    postgresql-client

ADD requirements_dev.txt requirements_dev.txt

ADD . $APPLICATION_ROOT

WORKDIR $APPLICATION_ROOT

RUN pip3 install pip -U && \
    pip3 install -r requirements_dev.txt

