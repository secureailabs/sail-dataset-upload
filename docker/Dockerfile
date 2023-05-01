FROM ubuntu:20.04

ENV TZ=America/Toronto
LABEL authors="prawal@secureailabs.com"
USER root

# Set time zone data
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install dependencies
RUN apt-get update && \
  apt-get -y upgrade && \
  apt-get install -y \
  nginx \
  wget \
  curl \
  sudo \
  git \
  build-essential \
  python3-pip \
  jq

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY docker/nginx.conf /etc/nginx/nginx.conf

COPY docker/Entrypoint.sh /Entrypoint.sh
RUN chmod +x /Entrypoint.sh

COPY sail_client-0.1.0-py3-none-any.whl /sail_client-0.1.0-py3-none-any.whl
RUN pip install --no-cache-dir /sail_client-0.1.0-py3-none-any.whl

COPY app /app

ENTRYPOINT [ "/Entrypoint.sh" ]
