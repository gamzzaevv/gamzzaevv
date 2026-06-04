FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps for WeasyPrint / psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libffi-dev libssl-dev \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements/production.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000
