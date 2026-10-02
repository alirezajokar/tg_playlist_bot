FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DB_PATH=/data/playlist.db

# unprivileged user; /data is the only writable place (SQLite file lives there)
RUN useradd --system --uid 10001 --no-create-home bot \
    && mkdir /data && chown bot:bot /data

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

USER bot
VOLUME ["/data"]
CMD ["python", "-m", "app"]
