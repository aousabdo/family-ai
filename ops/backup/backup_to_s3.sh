#!/bin/sh
set -eu

STAMP="$(date +%Y%m%d-%H%M)"
PGHOST="${DB_HOST:-db}"
PGDATABASE="${POSTGRES_DB:-familyai}"
PGUSER="${POSTGRES_USER:-family}"
PGPASSWORD="${POSTGRES_PASSWORD:-family}"
S3_BUCKET="${S3_BUCKET_CORPUS:-}"
VECTOR_BACKEND="${VECTOR_BACKEND:-pgvector}"

export PGPASSWORD

BACKUP_PATH="/backups/${PGDATABASE}-${STAMP}.dump"
pg_dump -Fc -h "$PGHOST" -U "$PGUSER" "$PGDATABASE" -f "$BACKUP_PATH"

if [ -n "$S3_BUCKET" ]; then
  aws s3 cp "$BACKUP_PATH" "s3://${S3_BUCKET}/db/${PGDATABASE}-${STAMP}.dump"
fi

if [ "$VECTOR_BACKEND" = "chroma" ]; then
  ARCHIVE="/backups/chroma-${STAMP}.tar.gz"
  if [ -d /data/chroma ]; then
    tar -czf "$ARCHIVE" -C /data chroma
    if [ -n "$S3_BUCKET" ]; then
      aws s3 cp "$ARCHIVE" "s3://${S3_BUCKET}/chroma/chroma-${STAMP}.tar.gz"
    fi
  fi
fi
