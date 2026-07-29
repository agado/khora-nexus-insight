#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# deploy.sh — Despliegue manual en producción
# Uso: ./scripts/deploy.sh
# Requiere: git pull ya hecho, .env configurado
# ──────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "==> Verificando .env..."
if [ ! -f .env ]; then
  echo "ERROR: .env no encontrado. Copia .env.example y configura las PROD_* variables."
  exit 1
fi

echo "==> Extrayendo variables requeridas..."
source <(grep -E '^PROD_' .env)

: "${PROD_JWT_SECRET:?ERROR: PROD_JWT_SECRET no está definido en .env}"
: "${PROD_DB_PASSWORD:?ERROR: PROD_DB_PASSWORD no está definido en .env}"

echo "==> Construyendo y arrancando contenedores..."
docker compose -f docker-compose.prod.yml up -d --build

echo "==> Esperando health check..."
sleep 5
if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
  echo "✅ Nexus Insight desplegado correctamente"
else
  echo "⚠️  Health check falló. Revisa logs:"
  docker compose -f docker-compose.prod.yml logs --tail=30
  exit 1
fi
