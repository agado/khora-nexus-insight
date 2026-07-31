#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# setup-vps.sh — Configuración única del VPS (idempotente)
# Uso: sudo bash setup-vps.sh   (requiere root)
# Nota: Caddy corre como contenedor (docker-compose.prod.yml), no en el host.
# Seguridad: el script nunca deja el servidor sin acceso SSH. El firewall abre
# primero el puerto SSH real y el hardening solo aplica si existe authorized_keys.
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

echo "==> Configurando firewall (ufw)..."
# Seguridad crítica: se detecta y abre el puerto SSH REAL antes de activar el
# firewall, para no perder el acceso a la máquina. Solo se exponen SSH/80/443.
SSH_PORT=$(ss -tlnp 2>/dev/null | awk '/sshd/ {split($4,a,":"); print a[2]; exit}')
[ -z "${SSH_PORT:-}" ] && SSH_PORT=22
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow "${SSH_PORT}/tcp" comment 'SSH'
ufw allow 80/tcp comment 'HTTP (Caddy)'
ufw allow 443/tcp comment 'HTTPS (Caddy)'
ufw --force enable
echo "   Firewall activo: SSH(${SSH_PORT}), 80, 443."

echo "==> Activando parcheo automático de seguridad..."
apt-get install -y unattended-upgrades
printf 'APT::Periodic::Update-Package-Lists "1";\nAPT::Periodic::Unattended-Upgrade "1";\n' > /etc/apt/apt.conf.d/20auto-upgrades
printf 'Unattended-Upgrade::Automatic-Reboot "false";\n' > /etc/apt/apt.conf.d/50nexus-unattended
echo "   Parcheo automático activo (sin reinicios automáticos)."

echo "==> Instalando cliente PostgreSQL (pg_dump para backups)..."
apt-get install -y postgresql-client

echo "==> Clonando/actualizando repositorio..."
if [ ! -d /opt/nexus-insight/.git ]; then
  git clone https://github.com/agado/khora-nexus-insight.git /opt/nexus-insight
else
  git -C /opt/nexus-insight pull origin main
  echo "   Repositorio ya existente, actualizado con git pull."
fi
cd /opt/nexus-insight

echo "==> Creando .env desde .env.example..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  Edita /opt/nexus-insight/.env con tus valores reales:"
  echo "     PROD_JWT_SECRET, PROD_DB_PASSWORD, SERVER_NAME (dominio o IP.sslip.io)"
else
  echo "   .env ya existe"
fi

echo "==> Generando secret de administración..."
if [ ! -f secrets/admin_password.txt ]; then
  mkdir -p secrets
  openssl rand -base64 32 > secrets/admin_password.txt
  chmod 600 secrets/admin_password.txt
  echo "   Secret generado en secrets/admin_password.txt"
else
  echo "   Secret ya existe"
fi

echo "==> Creando swap (2 GB) para RAM mínima..."
if swapon --show | grep -q '/swapfile'; then
  echo "   Swap /swapfile ya activo."
elif [ "$(free -m | awk '/^Swap:/{print $2}')" -gt 0 ]; then
  echo "   Swap existente detectado, sin cambios."
else
  fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none
  chmod 600 /swapfile
  mkswap /swapfile > /dev/null
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "   Swap de 2 GB creado y persistente (fstab)."
fi

echo "==> Hardening SSH (solo claves)..."
# Solo se deshabilita la contraseña si existe acceso por clave. Si no, se omite
# para garantizar que el operador nunca pierde el acceso al servidor.
if ls /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys > /dev/null 2>&1; then
  printf 'PasswordAuthentication no\n' > /etc/ssh/sshd_config.d/99-nexus-hardening.conf
  systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null || echo "⚠️  Reinicia SSH manualmente para aplicar hardening."
  echo "   SSH endurecido: autenticación por contraseña deshabilitada (solo claves)."
else
  echo "⚠️  No se detectó authorized_keys. Se OMITE el hardening SSH para no perder acceso."
fi

echo "==> Programando backup diario de la base de datos..."
mkdir -p /opt/nexus-insight/backups
cat > /etc/cron.d/nexus-backup <<'EOF'
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
0 3 * * * root cd /opt/nexus-insight && set -a && . ./.env && set +a && DB_PASSWORD="$PROD_DB_PASSWORD" DB_USER="$PROD_DB_USER" DB_NAME="$PROD_DB_NAME" DB_HOST=127.0.0.1 DB_PORT="${PROD_DB_PORT:-5432}" BACKUP_DIR=/opt/nexus-insight/backups /opt/nexus-insight/scripts/backup_db.sh >> /opt/nexus-insight/backups/backup.log 2>&1
EOF
chmod 644 /etc/cron.d/nexus-backup
echo "   Backup diario programado (03:00) en /opt/nexus-insight/backups (retención 7 días)."

echo "==> Programando limpieza semanal de Docker..."
cat > /etc/cron.d/nexus-docker-cleanup <<'EOF'
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
0 4 * * 0 root docker system prune -f --filter "until=72h" >> /opt/nexus-insight/backups/cleanup.log 2>&1
EOF
chmod 644 /etc/cron.d/nexus-docker-cleanup
echo "   Limpieza Docker semanal programada (domingo 04:00, imágenes inactivas > 72h)."

echo ""
echo "✅ VPS listo. Próximos pasos:"
echo "   1. nano /opt/nexus-insight/.env          (configurar PROD_* vars y SERVER_NAME)"
echo "   2. Abrir puertos 80 y 443 en el Security List de la VCN (Oracle Cloud)"
echo "   3. docker compose -f /opt/nexus-insight/docker-compose.prod.yml up -d --build"
echo ""
echo "ℹ️  Seguridad aplicada automáticamente:"
echo "   - Firewall ufw activo (solo SSH/80/443)."
echo "   - Parcheo automático de seguridad (sin reinicios automáticos)."
echo "   - Swap de 2 GB (evita OOM con 4 GB de RAM)."
echo "   - SSH por clave si existía authorized_keys."
echo "   - Backup diario de la base de datos (03:00, retención 7 días)."
echo "   - Limpieza semanal de imágenes Docker inactivas (disco 40 GB)."
