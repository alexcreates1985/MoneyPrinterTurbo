FROM ghcr.io/astral-sh/uv:0.12.12 AS uv
FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm
COPY --from=uv /uv /usr/local/bin/uv
USER root
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
USER vscode
