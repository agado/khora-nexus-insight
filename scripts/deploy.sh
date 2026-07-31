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
while IFS='=' read -r key val; do
  case "$key" in
    PROD_*|SERVER_NAME) export "$key"="${val}" ;;
  esac
done < <(grep -E '^(PROD_|SERVER_NAME)' .env)

fail() {
  echo "ERROR: $1"
  exit 1
}

echo "==> Pre-flight: validando variables de producción..."
[ -n "${PROD_JWT_SECRET:-}" ] || fail "PROD_JWT_SECRET no está definido en .env"
[ -n "${PROD_DB_PASSWORD:-}" ] || fail "PROD_DB_PASSWORD no está definido en .env"
[ -n "${PROD_DB_USER:-}" ] || fail "PROD_DB_USER no está definido en .env"
[ -n "${PROD_DB_NAME:-}" ] || fail "PROD_DB_NAME no está definido en .env"

case "${PROD_JWT_SECRET}" in
  *CHANGE_ME*) fail "PROD_JWT_SECRET contiene el placeholder CHANGE_ME. Define un secreto real." ;;
esac

if [ -z "${SERVER_NAME:-}" ] || [ "${SERVER_NAME}" = "localhost" ]; then
  fail "SERVER_NAME no configurado. Define el dominio o <IP>.sslip.io en .env (HTTPS)."
fi

if [ "${PROD_COMPANY_NAME:-Your Company}" = "Your Company" ]; then
  echo "⚠️  PROD_COMPANY_NAME sigue con el valor por defecto ('Your Company')."
fi

echo "   Validación correcta."

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
