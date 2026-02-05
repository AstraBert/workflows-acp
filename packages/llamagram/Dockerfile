FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# insall and run LlamaGram
RUN uv tool install llamagram
CMD [ "llamagram", "run" ]
