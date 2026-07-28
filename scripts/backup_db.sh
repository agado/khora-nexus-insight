#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_HOST="${DB_HOST:-db_service}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-nexus}"
DB_NAME="${DB_NAME:-nexus_db}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="${BACKUP_DIR}/nexus_db_${TIMESTAMP}.sql"
KEEP_DAYS="${KEEP_DAYS:-7}"

mkdir -p "$BACKUP_DIR"

PGPASSWORD="${DB_PASSWORD}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    -f "$FILENAME"

echo "Backup saved: $FILENAME"

find "$BACKUP_DIR" -name "nexus_db_*.sql" -mtime "+${KEEP_DAYS}" -delete
echo "Backups older than ${KEEP_DAYS} days removed."
