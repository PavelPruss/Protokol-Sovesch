FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

WORKDIR /app

# System packages:
# - ffmpeg is required by faster-whisper for audio/video decoding
# - build-essential helps compile some Python wheels when needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv and project dependencies first (better layer caching).
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
RUN uv sync --no-dev

# Copy project source code.
COPY . .

EXPOSE 8090

CMD ["uv", "run", "python", "web_app.py"]
