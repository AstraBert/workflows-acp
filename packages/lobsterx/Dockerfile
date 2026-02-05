FROM python:3.12-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create user
RUN useradd -m -u 1000 user

# Copy uv to system location
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Switch to user
USER user
ENV PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/workspace

# Install llamagram
RUN uv tool install lobsterx --prerelease=allow

CMD [ "lobsterx", "run" ]
