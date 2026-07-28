#!/usr/bin/env bash
# Khora Nexus Insight — PostgreSQL backup script
# Usage: DB_PASSWORD=<password> ./scripts/backup_db.sh
#
# Required env:
#   DB_PASSWORD             PostgreSQL password
#
# Optional env with defaults:
#   BACKUP_DIR  (./backups) Output directory
#   DB_HOST     (localhost) PostgreSQL host
#   DB_PORT     (5432)      PostgreSQL port
#   DB_USER     (nexus_db_user) PostgreSQL user
#   DB_NAME     (nexus_insight_db) Database name
#   KEEP_DAYS   (7)         Delete backups older than N days
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-nexus_db_user}"
DB_NAME="${DB_NAME:-nexus_insight_db}"
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
