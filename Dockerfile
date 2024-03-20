FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

RUN apt update -y && apt install --no-install-recommends -y ffmpeg

USER vscode

RUN pip install --user pdm

WORKDIR /app