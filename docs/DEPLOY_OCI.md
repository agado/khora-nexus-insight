# Despliegue en Oracle Cloud — Notas de operación

Documento complementario a la sección **"j — Evaluación"** del [`README.md`](../README.md). Recoge las trampas de red y la operativa de producción aprendidas durante el despliegue real del proyecto en un VPS de Oracle Cloud.

## Gotchas de red en OCI (causan "connection timed out")

- **Route table:** la subnet debe tener una regla `0.0.0.0/0 → Internet Gateway`. Una route table vacía deja la IP pública inalcanzable (ni SSH ni HTTP). Si el formulario solo permite "Private IP" como target, es que falta el Internet Gateway en la VCN: créalo primero.
- **Security List:** la creada por el wizard solo suele abrir SSH (22). Añade ingreso TCP **80 y 443** desde `0.0.0.0/0` **antes** de `deploy.sh`, o el smoke test y la emisión del certificado fallarán (el firewall de red de OCI actúa antes que `ufw`).
- **IP pública:** usa la del **VNIC** (no la privada `10.x.x.x`). Considera una IP pública **reservada** (estática) para que `SERVER_NAME` no cambie al detener/arrancar la instancia.
- **Campo cloud-init:** si la consola rechaza el script ("demasiado grande"), no es bloqueante — entra por SSH y ejecuta `sudo bash setup-vps.sh` a mano.

## Operativa en producción: rollback y restauración

**Rollback de código:** ante un despliegue defectuoso, se revierte al estado anterior **sin perder datos** (Postgres vive en el volumen `pgdata`):

```bash
cd /opt/nexus-insight
git tag                       # listar versiones estables
git checkout <tag-o-commit-anterior>
docker compose -f docker-compose.prod.yml up -d --build
```

**Restauración de la base de datos:** el backup diario genera `backups/nexus_db_*.sql` (retención 7 días). Para restaurar en una base vacía (p. ej. tras pérdida del volumen):

```bash
cd /opt/nexus-insight && set -a && source .env && set +a
PGPASSWORD="$PROD_DB_PASSWORD" psql -h 127.0.0.1 -p "${PROD_DB_PORT:-5432}" \
  -U "$PROD_DB_USER" -d "$PROD_DB_NAME" < backups/nexus_db_YYYYMMDD_HHMMSS.sql
```

**Validación post-deploy:** `scripts/deploy.sh` y el CD no validan `localhost:8000` sino el **perímetro completo** — `https://${SERVER_NAME}/api/v1/health` a través de Caddy + TLS (con retry de 120s para el arranque y 60s adicionales para la emisión del certificado). En el **primer** arranque la descarga del modelo (`qwen2.5:1.5b`, ~1 GB) puede alargar la puesta en marcha varios minutos; los reintentos posteriores son rápidos porque el modelo ya queda cacheado en el volumen `ollama_storage`.
