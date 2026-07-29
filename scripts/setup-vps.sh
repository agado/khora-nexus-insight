#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# setup-vps.sh — Configuración única del VPS
# Uso: chmod +x setup-vps.sh && ./setup-vps.sh
# ──────────────────────────────────────────────

echo "==> Actualizando sistema..."
apt-get update && apt-get upgrade -y

echo "==> Instalando Docker..."
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo "==> Verificando Docker..."
docker info > /dev/null 2>&1 || { echo "Docker no arrancó"; exit 1; }

echo "==> Instalando Caddy (HTTPS)..."
apt-get install -y debian-keyring debian-archive-keyring
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get install -y caddy

echo "==> Clonando repositorio..."
cd /opt
git clone https://github.com/agado/khora-nexus-insight.git nexus-insight
cd nexus-insight

echo "==> Creando .env desde .env.example..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  Edita /opt/nexus-insight/.env con tus valores reales (PROD_JWT_SECRET, etc.)"
  echo "   Luego ejecuta: docker compose -f docker-compose.prod.yml up -d --build"
else
  echo "   .env ya existe"
fi

echo ""
echo "✅ VPS listo. Próximos pasos:"
echo "   1. nano /opt/nexus-insight/.env   (configurar PROD_* vars)"
echo "   2. docker compose -f /opt/nexus-insight/docker-compose.prod.yml up -d --build"
echo "   3. Copiar Caddyfile a /etc/caddy/Caddyfile y configurar dominio/IP"
echo "   4. systemctl reload caddy"
