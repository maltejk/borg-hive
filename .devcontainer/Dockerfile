FROM python:3.12-slim-trixie

LABEL org.opencontainers.image.authors="malte@maltejk.de"
LABEL org.opencontainers.image.source="https://github.com/maltejk/borg-hive"

# set environment variables
ENV PYTHONDONTWRITEBYTE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get install -y acl libldap2-dev libmariadb-dev mariadb-client libsasl2-dev libssl-dev \
                       openssh-server sshfs libldap2-dev libssl-dev libpam-ldapd netcat-traditional \
                       rsync git libssl-dev openssl libacl1-dev libacl1 build-essential pkg-config

RUN useradd -m -s /bin/bash devcontainer

USER devcontainer

WORKDIR /deps

COPY requirements.txt .
COPY requirements-dev.txt .
COPY docs/requirements.txt requirements-docs.txt

SHELL ["/bin/bash", "-c"]
RUN python3 -m venv . \
    && source bin/activate \
    && pip install -r requirements.txt -r requirements-dev.txt -r requirements-docs.txt
