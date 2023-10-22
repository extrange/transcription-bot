FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt