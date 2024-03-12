FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

ENV TZ="Asia/Singapore"

RUN apt update -y && apt install --no-install-recommends -y ffmpeg

COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt