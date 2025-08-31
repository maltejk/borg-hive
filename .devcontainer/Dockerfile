FROM python:3.10-slim-bookworm AS base

LABEL org.opencontainers.image.authors="malte@maltejk.de"
LABEL org.opencontainers.image.source="https://github.com/maltejk/borg-hive"

FROM ghcr.io/astral-sh/uv:0.8.14 AS uv

FROM base

COPY --from=uv --chown=root:root /uv  /usr/local/bin/uv
COPY --from=uv --chown=root:root /uvx /usr/local/bin/uvx

# set environment variables
ENV PYTHONDONTWRITEBYTE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get install -y libmariadb-dev mariadb-client python3-pip libsasl2-dev python3-dev libldap2-dev libssl-dev libmariadb-dev \
                       python3-pip openssh-server sshfs acl libsasl2-dev python3-dev libldap2-dev libssl-dev libpam-ldapd netcat-traditional \
                       rsync git python3-dev libssl-dev openssl libacl1-dev libacl1 build-essential pkg-config

WORKDIR /deps

COPY requirements.txt .
COPY requirements-dev.txt .
RUN pip install -r requirements.txt -r requirements-dev.txt

RUN useradd -m -s /bin/bash devcontainer
