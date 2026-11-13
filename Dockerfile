FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

# Unprivileged user; /data holds the persistent search index (Docker volume).
RUN useradd --create-home --uid 10001 copilot \
    && mkdir -p /data \
    && chown copilot:copilot /data

COPY app ./app
COPY kb ./kb
COPY samples ./samples
# The evaluation CLI writes eval/results/*.md, so this folder belongs to the app user.
COPY --chown=copilot:copilot eval ./eval

USER copilot

ENV INDEX_PATH=/data/index.sqlite3 \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000
CMD ["python", "-m", "app"]
