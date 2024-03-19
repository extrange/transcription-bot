FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

USER vscode

RUN pip install --user pdm

WORKDIR /app