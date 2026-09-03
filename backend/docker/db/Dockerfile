ARG POSTGRES_BASE_IMAGE=public.ecr.aws/docker/library/postgres:16

FROM ${POSTGRES_BASE_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive
ARG PGVECTOR_PACKAGE_VERSION=0.8.6-1.pgdg13+1

RUN apt-get \
        -o Acquire::ForceIPv4=true \
        -o Acquire::Retries=3 \
        -o Acquire::http::Timeout=30 \
        update \
    && apt-get install -y --no-install-recommends \
        "postgresql-16-pgvector=${PGVECTOR_PACKAGE_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

LABEL org.opencontainers.image.title="Tuji PostgreSQL with pgvector" \
      org.opencontainers.image.source="https://apt.postgresql.org/" \
      org.opencontainers.image.version="pg16-pgvector-0.8.6"
