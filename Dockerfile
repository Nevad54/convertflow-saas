FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    fonts-liberation \
    fontconfig \
    libreoffice \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/.tmp/uploads /app/.tmp/outputs

# Koyeb / Railway / Heroku inject $PORT. Default to 8080 for local docker.
ENV PORT=8080
EXPOSE 8080

# Shell form so ${PORT} is expanded at container start.
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}
