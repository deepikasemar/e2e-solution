FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=43123 \
    DATABASE_PATH=/data/applyagent.sqlite

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY applyagent ./applyagent
COPY wsgi.py .

RUN mkdir -p /data
EXPOSE 43123

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % __import__('os').environ.get('PORT', '43123'))"

CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-43123} --timeout 120 wsgi:app"]
