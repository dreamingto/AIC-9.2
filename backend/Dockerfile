ARG PYTHON_BASE_IMAGE=public.ecr.aws/docker/library/python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=60 \
    PIP_RETRIES=10

WORKDIR /app

COPY requirements.lock ./
RUN pip install --requirement requirements.lock

COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
COPY data ./data

EXPOSE 8000
