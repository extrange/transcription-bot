FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

ENV TZ="Asia/Singapore"


# COPY requirements.txt /tmp/requirements.txt
# RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt
# USER vscode

# RUN curl -sSL https://pdm-project.org/install-pdm.py | python3 -