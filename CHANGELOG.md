# Changelog

## Unreleased — Observability & DevOps

### Added
- **Request ID tracing**: `X-Request-ID` header en todas las respuestas. Cada log incluye `request_id` para correlación.
- **Access log middleware**: Cada request registra `method`, `path`, `status`, `latency_ms`, `request_id` en JSON.
- **JSONFormatter**: Logs JSON dinámicos con campos extra sin perder los básicos.
- **Health v2**: Endpoint `/api/v1/health` ahora incluye `version`, `uptime_seconds`, `request_id`.
- **Graceful shutdown**: Conexiones DB se cierran limpiamente al detener el contenedor.
- **CI pipeline**: GitHub Actions ejecuta ruff → pytest → docker build en cada push/PR.
- **CD pipeline**: Workflow SSH definido para deploy automático al VPS. Pendiente de configuración del VPS y GitHub Secrets para activación.
- **Deploy scripts**: `scripts/setup-vps.sh` (bootstrap VPS idempotente) y `scripts/deploy.sh` (deploy manual). El setup aplica: firewall ufw (solo SSH/80/443, detectando el puerto SSH real antes de activar), parcheo automático de seguridad (sin reinicios), swap de 2 GB anti-OOM, y hardening SSH condicional a que exista `authorized_keys` (nunca deja al operador sin acceso).
- **Caddyfile**: Reverse proxy HTTPS integrado en `docker-compose.prod.yml` (Caddy como contenedor). Pendiente de definir `SERVER_NAME` en el `.env` del VPS y abrir puertos 80/443 en la VCN.
- **README**: Diagrama de red agnóstico de proveedor, tabla de requisitos mínimos del servidor y diagrama de filtrado por doble capa (Security + Cognitive Layer).
- **README**: Runbook de despliegue seguro en Oracle Cloud (cloud-init, tmux, recuperación por consola VNC).
- **README**: Operativa de producción — rollback de código (`git checkout <tag>` + compose up) y restauración del backup diario (`psql < nexus_db_*.sql`).

### Changed
- Tests: 267 (eran 265).
- `docker-compose.prod.yml`: rotación de logs Docker (`json-file`, 10m × 3) en los 4 servicios y puerto `127.0.0.1:5432` solo-loopback para backups locales (inaccesible desde el exterior).
- `scripts/setup-vps.sh`: instalación de `postgresql-client` y cron de backup diario de la DB (03:00, retención 7 días); cron semanal de limpieza de imágenes Docker (`docker system prune --filter until=72h`, domingo 04:00) para no llenar el disco de 40 GB.
- `scripts/deploy.sh`: pre-flight estricto antes de `docker compose up` — falla si faltan `PROD_DB_USER`/`PROD_DB_NAME`, si `PROD_JWT_SECRET` contiene el placeholder `CHANGE_ME`, o si `SERVER_NAME` está vacío/`localhost` (evita degradación silenciosa a HTTP); warning si `PROD_COMPANY_NAME` sigue con el default. Parser seguro de `.env` sin `source`/eval (admite valores con espacios tipo `PROD_COMPANY_NAME=Your Company`). Guard anti-filtrado: aborta si `.env` está trackeado por git.
- `scripts/deploy.sh` + CD: el smoke test valida el **perímetro completo** `https://SERVER_NAME/api/v1/health` a través de Caddy + TLS (retry 120s para el primer arranque), en lugar de `localhost:8000`; tras el alcance, verificación **estricta del certificado** (sin `-k`) que avisa si Let's Encrypt no emitió (DNS/80/443) sin bloquear arranques lentos.
- `.env.example`: documenta `PROD_COMPANY_NAME` (sección producción).
- `README`: preparación pre-deploy del `.env` (tabla de variables + generación de secretos con `openssl rand -base64`), recuperación de la contraseña `admin` (`cat secrets/admin_password.txt`) y sección **Primer uso (primer click)** — login → Subir PDF → Consultar. Badge de tests corregido (265 → 267).
- `scripts/setup-vps.sh`: instalación de Docker desde el repositorio de la **distro detectada** (`/etc/os-release` → `linux/ubuntu` o `linux/debian`). Antes hardcodeaba Debian y rompía el bootstrap en Ubuntu (Ampere A1) con 404 en `apt-get update`. Instalación **agnóstica e idempotente** vía helpers `ensure_cmd`/`ensure_file` (`command -v` → solo instala lo que falta: curl, gnupg, ca-certificates, docker, ufw, unattended-upgrades, postgresql-client, git, openssl, iproute2).
- `src/core/config.py`: Fail-Closed de `JWT_SECRET` ahora rechaza también el placeholder `CHANGE_ME_*` en producción (no solo el valor dev por defecto).
- README/SECURITY: correcciones de honestidad documental — perímetro Caddy como única excepción (SECURITY §2.9), claim de portabilidad agnóstico de proveedor, Opción 3 de despliegue real en VPS, credenciales de producción.
- README roadmap: H7.1/H7.2/H7.3 marcados como completados; **H7.4 (export .txt + CLI query) marcado como descartado por YAGNI** — nunca se implementó (confirmado en historial, commit `9eadcb5`).

### Security
- Request ID tracing (estaba en roadmap post-MVP, ahora implementado).

## v1.0.0 — Secure RAG Platform

> 9 hitos, 125+ commits, 0 dependencias cloud. De un scaffolding Docker a una plataforma RAG multi-departamental con Zero-Trust, auditoría forense e inferencia 100% local.

### Estrategia

El proyecto se construyó en espiral: primero infraestructura repetible, luego seguridad de identidad, luego ingesta documental, luego el core RAG, luego capa de gestión, y finalmente hardening — cada capa validada por tests antes de avanzar.

### Lo que se entregó

**Seguridad y Soberanía**
- Autenticación JWT (HS256) + Argon2id con middleware RBAC departamental — cada request valida identidad, rol y perímetro de acceso.
- Zero-Trust Network: PostgreSQL y Ollama sin puertos al host, solo accesibles desde FastAPI.
- Triggers inmutables en PostgreSQL para la tabla de auditoría — UPDATE/DELETE bloqueados a nivel de base de datos.
- Rate limiting (5 login/min por IP), CSP y security headers, política de complejidad OWASP en contraseñas, sanitización XSS en salida RAG.
- Ingesta con SHA-256 en memoria + validación de magic bytes + rechazo de duplicados.

**Motor RAG Local**
- Pipeline completo: consulta → filtro RBAC → contexto truncado (4K chars) → prompt anti-alucinación (`_NO_INVENT`) → Ollama (qwen2.5:1.5b) → respuesta sanitizada.
- Adaptación de tono por departamento/stakeholder (técnico, directivo, PM, legal) inyectada en tiempo de prompt.

**Gestión Documental**
- CRUD completo de documentos con ciclo de vida (subida, búsqueda textual, borrado).
- Soporte multi-departamento (M2M) con documentos de acceso público (is_public).
- Exportación de respuestas a .txt.

**Administración y UX**
- Interfaz web profesional (Jinja2 + htmx + Pico CSS) con login, dashboard, administración de usuarios CRUD, visor de registros de auditoría.
- CLI (`nexus.py upload|document|query`) para operaciones desde terminal.
- Sin JavaScript de compilación — sin dependencias JS runtime.

**Calidad y Reproducibilidad**
- 125+ commits con conventional commits, 190+ tests, pre-commit (lint + format) y pre-push (tests).
- Docker Compose single-command (`docker compose up --build`).
- Entorno productivo replicable con `docker-compose.prod.yml`.

### Lo que NO se entregó (intencionadamente)

- Búsqueda vectorial (ChromaDB) — el modelo qwen2.5:1.5b responde bien con contexto textual. La vectorización añade complejidad operativa sin mejora demostrable en este escenario.
- OCR — el MVP asume documentos digitales (PDF/texto). El OCR duplica la complejidad de ingesta sin validación de demanda real.
- CI/CD — GitHub Actions está preparado pero no activado. El entorno es 100% portable a cualquier proveedor cloud sin cambios arquitectónicos.

### Commit History

```text
h9.5   Refactor: splitting, DRY, data-driven seed, test hardening
h9.4   Security hardening: Fail Secure, JWT default warning, backups, resource limits
h9.3   UX: password confirm + real-time validation in create/reset forms
h9.2   Quality: deduplicated upload validation, logging, CSP, XSS, magic bytes
h9.1   Rate limiting: 5 POST/min per IP sliding window
h9     OWASP hardening: CSP, security headers, password policy, error sanitization
h8     Corporate experience: visual overhaul, tone adaptation, user admin CRUD
h7     Document lifecycle: delete, is_public, user CRUD, export .txt, CLI query
h6     Audit: Alembic migration, immutable trigger, AuditLog, web viewer
h5     RAG engine: RBAC-filtered query, Ollama integration, prompt engineering
h4     Ingestion: upload API + web + CLI, SHA-256 dedup, pypdf extraction
h3     Auth: JWT + Argon2id + RBAC middleware + login endpoint
h2     Foundation: nexus.py, async DB, Alembic, seed, 81 tests
h1     Scaffolding: Docker, FastAPI, health endpoint, 13 tests
```

---

## h9.5 — Refactoring & Quality (2026-07)

### Added
- Data-driven seed users via `_SEED_USER_DEFS` tuples (KISS)
- Extracted `_validate_role_value` and `_form_data()` closure for DRY error rendering
- Split `users.py` into `api_users.py` and `web_users.py` (KISS #6)

### Changed
- All AsyncMock mocks use `spec=AsyncSession` for type safety
- Async generator overrides for session fixtures

---

## h9.4 — Fail Secure & Backup Infrastructure (2026-07)

### Added
- `pg_dump` backup script with env-var-driven config
- `Fail Secure` + `Secure by Default` validation for JWT secret
- TDD test for JWT default warning
- Ollama resource limits in prod compose file
- `.env` configuration warning in README

### Fixed
- JWT default-secret warning now blocks startup in production
- `backups/` added to `.gitignore`
- Build verification without `.env` file

---

## h9.3 — Password UX & Validation (2026-07)

### Added
- Password confirm field in create and reset forms
- Real-time validation (green/red checklist) via `_password_field.html` partial
- Form data preservation on validation errors (OWASP — password never re-sent)

### Fixed
- Removed `token.txt` from tracking
- Deduplicated `AGENTS.md` / `agents.md`

---

## h9.2 — Quality & Hardening (2026-07)

### Added
- CSP + security headers on all responses (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)
- XSS sanitization: `marked.parse()` + DOMPurify, `rel="noopener noreferrer"` on all links
- Magic bytes PDF validation on web upload
- Generic RAG error message (internal errors never exposed to client)
- JS extracted to `static/js/main.js` (zero inline JS)

### Changed
- Deduplicated upload validation logic between JSON API and web endpoints
- Added structured logging to `document_service` and `user_service`

---

## h9.1 — Brute Force Protection (2026-07)

### Added
- In-memory sliding window rate limiter: 5 POST requests per minute per IP on `/api/v1/auth/login`
- Returns `429 Too Many Requests` with `Retry-After` header

---

## h9 — OWASP Security Baseline (2026-07)

### Added
- `Content-Security-Policy` (scripts/styles limited to `self` + CDNs)
- `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`
- Password complexity policy: ≥8 chars, uppercase, lowercase, digit, special char
- Applied on user creation and password reset

---

## h8 — Corporate Experience & User Administration (2026-07)

### Added
- Visual overhaul: Pico CSS theme, custom favicon, Inter font, system color scheme
- Audience selector in query form (PM / DEV / RRHH / General)
- Prompt adaptation: technical depth and tone shift dynamically based on target audience
- User administration CRUD (admin only):
  - List, create, edit, delete users
  - Role and department assignment
  - Accessible departments via multi-select
  - Password reset with OWASP validation
  - HTMX navigation within the Users tab
  - Toast feedback for every action
- Audit logging for every user admin action

---

## h7 — Document Lifecycle & CLI (2026-06)

### Added
- `DELETE /api/v1/documents/{id}` with RBAC (admin/lead can delete, staff cannot)
- `is_public` column: cross-department document visibility
- Web delete button (conditional on role)
- Full user CRUD API (`/api/v1/users/`) with 34 tests
- Export answer to `.txt` button in query result
- `nexus.py query` CLI command

---

## h6 — Immutable Audit Trail (2026-06)

### Added
- Alembic migration for `audit_log` table
- PostgreSQL trigger: `REJECT` on `UPDATE`/`DELETE` (append-only)
- `AuditLog` records on login, document upload, document delete
- `/web/logs` viewer with paginated table

---

## h5 — RAG Engine (2026-06)

### Added
- `POST /api/v1/rag/query` endpoint
- Role-scoped document retrieval: query only searches documents in user's accessible departments
- Ollama integration with configurable model, host, timeout
- Prompt engineering:
  - XML-style delimiters for context injection (anti-injection)
  - `_NO_INVERT` instruction: model must answer only from provided context
  - Temperature 0.1 for deterministic output
- Context truncation to 4000 characters (qwen2.5:1.5b context window)
- Frontend query form with multi-select document picker
- CLI query via `nexus.py query`

---

## h4 — Document Ingestion (2026-06)

### Added
- `POST /api/v1/documents/upload` endpoint
- SHA-256 hash computed in memory before storage (duplicate rejection)
- Magic bytes PDF validation (`%PDF`)
- PyPDF text extraction (fallback to UTF-8 plain text)
- Department-scoped document listing (`GET /api/v1/documents/`)
- Web frontend: login, dashboard, upload form, document list, logout
- Jinja2 + htmx + Pico CSS (no JS build step)
- CLI: `nexus.py upload`, `nexus.py document get`, `nexus.py document list`
- 167 tests

### Changed
- User-department relationship: migrated from single `department_id` to M2M `user_department`
- JWT payload now includes `role_level`, `accessible_departments`

---

## h3 — Authentication & RBAC (2026-05)

### Added
- `POST /api/v1/auth/login` with JWT (HS256) + Argon2id password hashing
- `get_current_user` dependency: validates token, enforces expiry
- `require_role` dependency: granular role-level access (admin=3, lead=2, staff=1)
- `require_department_access` dependency: document-level isolation
- Anti-enumeration: generic "Invalid credentials" message
- 8 tests

---

## h2 — Foundation Layer (2026-05)

### Added
- `nexus.py` CLI: `dev`, `prod`, `test`, `cov` commands
- Async SQLAlchemy 2.0 engine with `asyncpg`
- Alembic migrations framework
- Database models: `User`, `Department`, `Document`, `AuditLog`
- Seed script with 8 users across 3 departments
- `docker compose up --build` single-command deployment
- 81 tests

---

## h1 — Scaffolding (2026-05)

### Added
- Docker + Docker Compose setup with FastAPI, PostgreSQL, Ollama
- `GET /api/v1/health` endpoint
- `GET /` root redirect to `/docs`
- Project structure: `src/`, `tests/`, config, ruff, pre-commit
- 13 tests
