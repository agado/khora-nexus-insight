# Nexus Insight

[![CI](https://github.com/agado/khora-nexus-insight/actions/workflows/ci.yml/badge.svg)](https://github.com/agado/khora-nexus-insight/actions/workflows/ci.yml)
![Python 3.13](https://img.shields.io/badge/python-3.13-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![Docker](https://img.shields.io/badge/docker_compose-single--command-2496ED?logo=docker)
![Tests](https://img.shields.io/badge/tests-273-green)
![RAG](https://img.shields.io/badge/RAG-100%25_local-7B1FA2?logo=ollama)
![License](https://img.shields.io/badge/license-All_Rights_Reserved-red)
[![Conventional Commits](https://img.shields.io/badge/conventional%20commits-1.0.0-FE5196?logo=conventionalcommits)](https://conventionalcommits.org)

**Inferencia RAG 100% local, Zero-Trust, multi-departamento. Sin APIs cloud, sin costes por token, sin fugas de datos.**

Nexus Insight es un backend de análisis documental inteligente que permite a organizaciones en sectores regulados (banca, salud, administración pública, investigación) desplegar un asistente GenAI sobre su propia documentación técnica y estratégica — sin que un solo byte salga de su infraestructura.

El core del producto es su **Dual-Layer Filtering**: (1) aislamiento departamental estricto por RBAC + Zero-Trust network, y (2) adaptación cognitiva del output según el rol del destinatario (técnico, directivo, PM, legal). Todo sobre un modelo local Qwen2.5 1.5B vía Ollama, sin depender de OpenAI, Anthropic ni ninguna API externa.

**Para quién:** equipos de seguridad y cumplimiento que necesitan adoptar IA generativa sin fuga de datos, PM que traducen documentación técnica en insights estratégicos, y organizaciones que buscan una GenAI privada, sin costes por token ni dependencia de APIs cloud.

## a. Descripción general del proyecto

<details open> <summary>Descripción para técnicos</summary>

Nexus Insight es una plataforma de análisis documental inteligente diseñada bajo el paradigma Zero ‑Trust y una arquitectura monolito modular. Su objetivo es permitir la ingesta, procesamiento e inferencias RAG 100% locales, garantizando que la información confidencial nunca abandone la infraestructura física del cliente.

La IA se ejecuta en un contenedor aislado dentro de una red interna de Docker, cumpliendo los requisitos de soberanía de datos y seguridad corporativa.

Puntos clave para técnicos:

Seguridad y soberanía: Arquitectura y ejecución local para máxima privacidad. El entorno se controla con la variable `NEXUS_ENV` (development/production).

Modularidad: Diseño escalable y mantenible.

Tecnología: Uso de FastAPI, PostgreSQL, SQLAlchemy asíncrono y Ollama para IA local.

Observabilidad: Logs JSON estructurados para diagnóstico y monitoreo, facilitando la detección rápida de errores y el análisis de rendimiento.

</details>

<details> <summary>Descripción para negocio</summary>

Nexus Insight es una solución segura y local para analizar documentos importantes dentro de la infraestructura de la empresa, sin que la información sensible salga de sus sistemas. Esto garantiza privacidad y cumplimiento normativo mientras se aprovecha la inteligencia artificial para obtener insights valiosos.

Puntos clave para negocio:

Privacidad y cumplimiento: Protección de datos sensibles y normativas.

Valor de negocio: Insights accionables para mejorar procesos.

Confianza: Solución local que evita riesgos de fuga de información.

</details>

<details> <summary>Descripción para marketing</summary>

Nexus Insight ofrece una plataforma innovadora que combina seguridad de datos y tecnología avanzada de inteligencia artificial para transformar la gestión documental. Ideal para empresas que buscan maximizar el valor de su información sin comprometer la privacidad.

Puntos clave para marketing:

Innovación: Tecnología avanzada y diferenciadora.

Seguridad: Mensaje claro de protección de datos.

Transformación: Impacto positivo en la gestión documental.

</details>

<details> <summary>Descripción para PMs y Producto</summary>

Nexus Insight está diseñado para ofrecer a los equipos de producto y gestión una visión clara y segura del análisis documental, facilitando la toma de decisiones basada en datos sin comprometer la privacidad ni la seguridad.

Puntos clave para PMs y Producto:

Visión estratégica: Datos confiables para decisiones informadas.

Seguridad: Cumplimiento y privacidad garantizados.

Facilidad de uso: Plataforma accesible para equipos multidisciplinares.

</details>

## b. Stack tecnológico utilizado

* Backend: FastAPI (ASGI) sobre Python 3.13.
* Validación: Pydantic v2 (tipado estricto).
* Base de datos: PostgreSQL 16 + SQLAlchemy 2.0 (async con asyncpg).
* IA Local: Ollama ejecutando el modelo qwen2.5:1.5b en contenedor aislado.
* Infraestructura: Docker + Docker Compose.
* Automatización: `nexus.py` (MVP).
* Calidad de código: Ruff + pre‑commit + pre‑push (tests).
* Pruebas: Pytest + pytest-asyncio con mocking.

## c. Instalación y ejecución

Guía completa para poner el proyecto en funcionamiento desde un equipo con las herramientas base instaladas.

### Prerrequisitos

- Python 3.13+
- Docker + Docker Compose
- Git

### Pasos

0. Clonar el repositorio
```bash
git clone https://github.com/agado/khora-nexus-insight.git
cd nexus-insight
```

1. Configurar variables de entorno

> **IMPORTANTE:** Edita `.env` con tus valores reales. Por defecto incluye credenciales de desarrollo inseguras (ver `check_jwt_secret()`). En producción, `nexus.py prod` valida que `PROD_JWT_SECRET` esté definida y no sea el valor por defecto.

```bash
cp .env.example .env
```

Abre `.env` y personaliza al menos `JWT_SECRET` (desarrollo) o `PROD_JWT_SECRET` (producción).

2. Preparar el entorno Python local (necesario para herramientas de desarrollo: hooks, lint, tests)
<details>
<summary>Windows (PowerShell 7+)</summary>

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
</details>

<details>
<summary>Linux / macOS</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
</details>

3. Instalar hooks de git (se ejecutan automáticamente al commitear y al hacer push)
```bash
pre-commit install
pre-commit install --hook-type pre-push
```

4. Desplegar la infraestructura (API, base de datos, motor de IA)

> También disponible vía `python nexus.py dev` en cualquier OS.

<details>
<summary>Windows (PowerShell 7+)</summary>

```powershell
docker compose up --build
```
</details>

<details>
<summary>Linux / macOS</summary>

```bash
docker compose up --build
```
</details>

> El seed de datos de prueba (usuarios, departamentos) se ejecuta automáticamente al arrancar.

5. Inicializar el modelo de IA (solo la primera vez)
```bash
docker compose exec ollama_service ollama run qwen2.5:1.5b
```

6. Acceder a la documentación interactiva de la API

http://localhost:8000/docs

## d. Estructura del proyecto

```text
nexus-insight/
├── docker-compose.yml               ← entorno dev (single-command)
├── docker-compose.prod.yml          ← entorno producción (Caddy + HTTPS)
├── Dockerfile
├── Caddyfile                        ← reverse proxy HTTPS (producción)
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── alembic.ini / pytest.ini / ruff.toml / requirements.txt
├── nexus.py                         ← CLI de desarrollo y operación
├── agents.md
├── SECURITY.md                      ← invariantes de seguridad
├── SPEC.md
├── migrations/                      ← migraciones Alembic
│   └── versions/
├── scripts/                         ← operativa del ciclo de vida
│   ├── setup-vps.sh                 ← bootstrap idempotente del VPS
│   ├── deploy.sh                    ← despliegue con pre-flight
│   └── backup_db.sh                 ← backup diario de PostgreSQL
├── docs/                            ← documentación complementaria
├── src/
│   ├── main.py                      ← entry point
│   ├── api/
│   │   └── v1/                      ← endpoints (controllers)
│   │       ├── auth.py              ← login JWT
│   │       ├── documents.py         ← CRUD documentos
│   │       ├── health.py            ← health check
│   │       ├── api_users.py         ← API endpoints usuarios
│   │       ├── web_users.py         ← Web endpoints usuarios
│   │       ├── rag.py               ← endpoint RAG API
│   │       └── web.py               ← frontend web (Jinja2/htmx)
│   ├── core/
│   │   ├── config.py                ← settings
│   │   ├── database.py              ← DB engine
│   │   ├── seed.py                  ← datos de prueba
│   │   ├── auth/                    ← JWT, RBAC, seguridad
│   │   ├── middleware/              ← request_id + access log
│   │   ├── services/                ← use cases (business logic)
│   │   └── storage/                 ← file I/O
├── templates/                       ← Jinja2 (interfaz web)
├── static/
│   ├── css/theme.css
│   └── js/main.js
└── tests/                           ← refleja src/
    ├── conftest.py
    └── test_deployment.py
```

## e. Funcionalidades principales

* **Interfaz web profesional**: Login, dashboard y gestión de documentos con Jinja2 + htmx + Pico CSS. Redirección inteligente según sesión. Sin dependencias JavaScript de compilación.

* **CLI de documentos**: Subida (`nexus.py upload`), consulta (`nexus.py document get`) y listado (`nexus.py document list`) desde terminal. Consume la misma API que el frontend.

* **Autenticación segura**: Login con cookie httpOnly + SameSite=Lax. Cierre de sesión. Redirección automática a `/login` si no hay sesión válida. Anti-enumeración (mensaje genérico "Credenciales inválidas").

* **Control de acceso por roles y departamentos**: Jerarquía de roles (admin=3, lead=2, staff=1). Acceso aislado por departamento vía tabla M2M `user_department`. JWT transporta `user_id`, `role`, `accessible_departments`.

* **Protección anti-fuerza bruta**: Rate limiting de 5 intentos por minuto por IP en el endpoint de login. Middleware in-memory con ventana deslizante.

* **Seguridad en headers HTTP**: `Content-Security-Policy` (scripts/style limitados a `self` + CDNs), `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` en todas las respuestas.

* **Política de complejidad de contraseñas**: Validación OWASP (≥8 caracteres, mayúscula, minúscula, dígito, carácter especial) en creación y reseteo de contraseñas.

* **Ingesta con validación criptográfica**: Cálculo de SHA‑256 en memoria antes de almacenar metadatos. Validación de tipo de archivo por magic bytes (%PDF). Límite de 10 MB.

* **Extracción de texto**: PyPDF para PDFs, fallback a UTF-8 para texto plano.

* **Protección antiduplicados**: Rechazo automático de documentos con SHA-256 duplicado.

* **Flujo RAG 100% local**: Recuperación contextual por rol + generación en contenedor aislado de Ollama. Prompt anti-alucinación (`_NO_INVENT`) que restringe al modelo a usar solo el contexto proporcionado, adaptado para el modelo Qwen2.5 1.5B.

* **Auditoría inmutable (Zero‑Trust)**: Tabla append‑only con triggers que bloquean UPDATE/DELETE.

* **Administración de usuarios (admin)**: CRUD completo desde interfaz web con edición de rol, departamento y departamentos accesibles. Validación OWASP y auditoría de cada acción.

* **UX de creación de usuarios**: Formulario con requisitos visibles de contraseña, campo de confirmación, validación en tiempo real (checklist verde/roja), y preservación de datos del formulario en errores de validación (sin reenviar la contraseña por seguridad OWASP).

* **Observabilidad nativa**: Logs JSON estructurados sin latencia de red.

### Arquitectura de Red y Soberanía de Datos (Zero-Trust)

El sistema implementa un perímetro de seguridad donde los servicios de persistencia e inferencia están completamente aislados del exterior. El contenedor **Caddy** (HTTPS) actúa como el único punto de entrada autorizado.

```mermaid
flowchart TB
    subgraph Host_VPS [Servidor / VPS]
        subgraph Zona_Publica [Zona Publica - Firewall 80/443]
            Caddy[Contenedor Caddy<br/>HTTPS 443 / HTTP 80<br/>unico punto de entrada]
        end

        subgraph Docker_Network [Red Interna Privada: nexus-network]
            API[Backend FastAPI<br/>127.0.0.1:8000<br/>JWT + RBAC]
            DB[(PostgreSQL<br/>5432)]
            Ollama[Servidor Ollama<br/>11434]

            Caddy -- "red interna<br/>fastapi_app:8000" --> API
            API -- "1. Persistencia / Consulta" --> DB
            API -- "2. Contexto RAG<br/>HTTP interno" --> Ollama
        end
    end

    User([Cliente / Evaluador]) -- "HTTPS 443<br/>TLS 1.3" --> Caddy

    Internet([Internet]) -.->|"BLOQUEADO<br/>solo 80/443 via Caddy"| API
    Internet -.->|"BLOQUEADO<br/>sin puertos expuestos"| DB
    Internet -.->|"BLOQUEADO<br/>sin puertos expuestos"| Ollama
    Ollama -.->|"BLOQUEADO<br/>sin acceso directo"| DB

    style Caddy fill:#ff7f0e,stroke:#fff,color:#fff
    style API fill:#1f77b4,stroke:#fff,color:#fff
    style DB fill:#2ca02c,stroke:#fff,color:#fff
    style Ollama fill:#9467bd,stroke:#fff,color:#fff
```


#### Requisitos Mínimos del Servidor

El stack es **agnóstico de proveedor**: funciona en cualquier VPS o VM (Oracle Cloud, Hetzner, Contabo, etc.) que cumpla los requisitos mínimos, tanto en arquitectura x86_64 como ARM64.

| Recurso | Mínimo (con Ollama) | Recomendado |
|---|---|---|
| **CPU** | 2 vCPU | 4 vCPU |
| **RAM** | 4 GB | 8 GB |
| **Disco** | 15 GB SSD | 40 GB SSD |
| **Arquitectura** | x86_64 / ARM64 | ARM64 (mejor coste/rendimiento) |
| **Sistema** | Debian 12 / Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| **Puertos abiertos** | 80, 443 (+22 SSH para administración) | idéntico |

Desglose de consumo por contenedor (techos configurados): FastAPI ~1 GB, PostgreSQL ~2 GB, Ollama + Qwen2.5-1.5B ~8 GB, Caddy ~50 MB. El modelo `qwen2.5:1.5b` se descarga automáticamente al primer arranque e infiere en CPU (sin GPU).

#### Pilares del Diseño de Seguridad y Soberanía de Datos

Este modelo arquitectónico soluciona de raíz los riesgos de filtración de datos y ataques perimetrales mediante tres principios de diseño:

* **Soberanía de Datos Absoluta (Inferencia 100% Local):**
    * **Consumo sin fugas:** A diferencia de las APIs comerciales (OpenAI, Anthropic), el procesamiento del modelo `qwen2.5:1.5b` ocurre de forma confinada dentro del contenedor local de **Ollama** (`ollama/ollama:latest`).
    * **Sin telemetría externa:** Ni los datos del usuario, ni los fragmentos de los documentos inyectados en el contexto, ni los prompts de consulta viajan por internet ni son compartidos para entrenar modelos externos.
* **Aislamiento de Red Zero-Trust (Cortafuegos Perimetral):**
    * **Invisibilidad de servicios:** PostgreSQL (puerto `5432`) y Ollama (puerto `11434`) operan en la red virtual privada `nexus-network` **sin mapear o exponer puertos hacia el host exterior**. Son invisibles ante escaneos de puertos en la máquina física.
    * **Punto único de acceso:** El contenedor **Caddy** (HTTPS, puertos `80/443`) actúa como el único perímetro autorizado hacia el exterior. Ningún comando externo puede interactuar directamente con la base de datos o con el motor de IA sin pasar por Caddy y ser interceptado por el middleware de validación criptográfica (JWT) y el control de accesos (RBAC).
* **Modularidad Operativa (Acoplamiento Suelto):**
    * **Independencia de servicios:** La infraestructura está diseñada para permitir el encendido, apagado o actualización de cada máquina por separado (`docker compose up <servicio>`). 
    * **Fácil mantenimiento:** Si se requiere aislar Ollama por mantenimiento, actualizar a una versión más segura o auditar la base de datos de manera aislada, el ecosistema lo permite sin comprometer la integridad o la estabilidad del resto de módulos del backend.

#### Flujo Lógico: Filtrado por Doble Capa

El diferencial frente a un RAG genérico: cada consulta atraviesa dos capas de filtrado antes de llegar al modelo.

```mermaid
flowchart LR
    subgraph Capa_Seguridad [Security Layer - Aislamiento]
        S1[JWT + Argon2id]
        S2[RBAC departamental<br/>admin / lead / staff]
        S3[Filtro RAG<br/>solo documentos de su dept.]
    end
    subgraph Capa_Cognitiva [Cognitive Layer - Adaptación]
        C1[Prompt engineering<br/>tono/formato por audiencia]
        C2[Contexto 4K chars +<br/>anti-alucinación _NO_INVENT]
        C3[Inferencia 100% local<br/>Qwen2.5 1.5B en Ollama]
    end
    Q[Usuario: consulta + audiencia] --> S1 --> S2 --> S3
    S3 --> C1 --> C2 --> C3
    C3 --> R[Respuesta adaptada<br/>al perfil del receptor]
```

## f. Usuario y contraseña de prueba

* Credenciales de desarrollo incluidas en `.env.example`:

| Usuario | Rol | Departamento | Acceso a departamentos | Contraseña |
|---|---|---|---|---|
| `admin` | admin | IT | Todos los departamentos | `admin123` |
| `lead_it` | lead | IT | IT | `lead123` |
| `lead_hr` | lead | RRHH | RRHH | `lead123` |
| `lead_pm` | lead | PM | PM | `lead123` |
| `staff_it` | staff | IT | IT | `staff123` |
| `staff_hr` | staff | RRHH | RRHH | `staff123` |
| `staff_pm` | staff | PM | PM | `staff123` |
| **`ceo`** | **admin** | **IT** | **Todos los departamentos** | `ceo123` |

Jerarquía de roles: `admin` (nivel 3) > `lead` (nivel 2) > `staff` (nivel 1).

(Nunca usar estas credenciales en producción.)

**Producción:** el seed crea únicamente el usuario `admin`, cuya contraseña se genera aleatoriamente en `scripts/setup-vps.sh` y se almacena en `secrets/admin_password.txt` del VPS (accesible vía Docker secret, nunca en el repositorio). Acceso del evaluador por HTTPS: `https://<SERVER_NAME>` con el usuario `admin` y esa contraseña (obtenerla con `cat /opt/nexus-insight/secrets/admin_password.txt`).



> Historial completo de versiones en [`CHANGELOG.md`](./CHANGELOG.md).

## g. Roadmap de Desarrollo (TDD)

| Hito | Objetivo | Criterio de Aceptación (DoD) |
|---|---|---|
| **H1** ✅ | Scaffolding: Docker, FastAPI, health endpoints | `GET /api/v1/health` responde 200. 13 tests. |
| **H2** ✅ | `nexus.py`, base de datos, migraciones Alembic, modelos (`+department_id`), seed, test integración DB, `pytest-cov` | `nexus dev` funciona. Tablas creadas. Seed poblado. |
| **H3** ✅ | Autenticación JWT + Argon2id + middleware RBAC | Login OK → 200. Sin token → 401. Prohibición por rol → 403. |
| **H4** ✅ | Ingesta documental por API + frontend web + CLI: SHA-256, extracción texto (pypdf), búsqueda textual, roles (admin/lead/staff), departamentos M2M, login web, dashboard, upload, lista documentos, logout, CLI upload/get/list | Upload → 200/409. 167 tests. Frontend funcional. CLI funcional. |
| **H5** ✅ | Motor RAG: consulta con filtro RBAC, contexto a Ollama, delimitadores XML anti-inyección + sanitización OWASP, truncado de contexto a 4K chars, endpoint API + frontend web + CLI | `POST /api/v1/rag/query` → 200. 186 tests. Frontend Consultar funcional. |
| **H6** ✅ | Auditoría y trazabilidad: Alembic, trigger PostgreSQL inmutable, AuditLog completo, visor Registros | Ver detalle abajo ↓ |
| **H7** ✅ | Ciclo de vida documental: borrar docs, is\_public, CRUD usuarios. H7.4 (export .txt + CLI query) descartado por YAGNI. | Ver detalle abajo ↓ |
| **H8** ✅ | Experiencia corporativa: mejora visual, adaptación de tono por departamento/stakeholder, administración de usuarios | Ver detalle abajo ↓ |
| **H9** ✅ | Seguridad: rate limiting (login 5/min), CSP + security headers, password complexity policy | Ver detalle abajo ↓ |

### H6 — Auditoría y trazabilidad

| Código | Objetivo | Criterio de Aceptación |
|--------|----------|------------------------|
| **H6.1** ✅ | Alembic funcional + migration trigger inmutable en audit_log | `alembic upgrade head` crea tablas + trigger. Rollback funcional. |
| **H6.2** ✅ | AuditLog en login/upload/delete + visor Registros en frontend | Login, subida y borrado → fila en `audit_log`. Pestaña Registros muestra tabla paginada. |

### H7 — Ciclo de vida documental

| Código | Objetivo | Criterio de Aceptación |
|--------|----------|------------------------|
| **H7.1** ✅ | Borrar documentos (admin/lead) + staff sin subir | `DELETE /api/v1/documents/{id}` → 200/404/403. Botón frontend. |
| **H7.2** ✅ | Documento de acceso general (`is_public`) | Columna. Bypass del filtro departamental en listado + RAG. |
| **H7.3** ✅ | CRUD usuarios (admin) | Alta/baja/modificación de usuarios desde frontend. API completa. 34 tests. |
| **H7.4** | Exportar respuesta .txt + CLI query | Descartado por YAGNI (no implementado). La consulta web de H5 incluye copiar respuesta al portapapeles. |

### H8 — Experiencia corporativa

| Código | Objetivo | Criterio de Aceptación |
|--------|----------|------------------------|
| **H8.1** ✅ | Mejora visual (tema Pico CSS, logo, tipografía) | Aspecto corporativo, coherente con la marca. 0 inline styles. |
| **H8.2** ✅ | Adaptación de tono por departamento/stakeholder | Selector de audiencia en consulta. El prompt se adapta automáticamente. |
| **H8.3** ✅ | Administración de usuarios (web) | Lista, crear, editar, eliminar, resetear contraseña desde pestaña Usuarios. Navegación HTMX dentro del tab. Feedback visual con toasts. Validación OWASP (rol, departamentos accesibles, unicidad). Auditoría de cada acción. |

### H9 — Seguridad (OWASP)

| Código | Objetivo | Criterio de Aceptación |
|--------|----------|------------------------|
| **H9.1** ✅ | Rate limiting en login (5 POST/min por IP) | 6ª petición en 1 minuto → 429 Too Many Requests. Middleware in-memory sliding window. |
| **H9.2** ✅ | CSP + security headers en todas las respuestas | `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`. |
| **H9.3** ✅ | Password complexity policy | ≥8 caracteres, ≥1 mayúscula, ≥1 minúscula, ≥1 dígito, ≥1 especial. Aplicado en crear y resetear contraseña. |
| **H9.4** ✅ | XSS sanitization en salida RAG | `marked.parse()` sanitizado con DOMPurify. Todos los enlaces con `rel="noopener noreferrer"`. |
| **H9.5** ✅ | Magic bytes en subida web | Validación `%PDF` en `POST /web/upload` (idéntico al endpoint API). |
| **H9.6** ✅ | Error RAG genérico (no exponer internos) | `str(exc)` reemplazado por "Error al procesar la consulta". El error real se loguea. |
| **H9.7** ✅ | JS extraído a archivo estático | `static/js/main.js` con `let`/`const`. Sin JS inline en templates. |

### Post-MVP (Futuro)

| Dimensión | Mejora prevista |
|---|---|
| **Seguridad** | Guardrails anti-prompt-injection completos. Rotación automática de claves JWT. Autenticación multifactor (TOTP). Rate limiting por usuario. |
| **IA y Búsqueda** | ChromaDB para búsqueda semántica vectorial. Multi-modelo (selección configurable entre qwen, llama, mistral). OCR para documentos escaneados. |
| **Infraestructura** | Orquestación con Docker Swarm o Kubernetes para alta disponibilidad. Monitoring con Prometheus + Grafana. Despliegue multi-entorno (staging, producción). |
| **Observabilidad** | OpenTelemetry para trazabilidad distribuida avanzada. Dashboard de métricas en tiempo real (latencia, consultas, errores). Alertas automáticas. Actualmente: `request_id` en logs + access log middleware. |
| **UX** | Nexus CLI completo con Typer + Rich (menús interactivos, barras de progreso, colores). Hot Folders para arrastrar y soltar documentos. Panel web de administración (React/Vue). |
| **Operaciones** | Políticas de retención de datos (limpieza automática). Exportación/importación de documentos y configuraciones. Notificaciones webhook al completar procesos. |
| **Ingesta** | Procesamiento por lotes (batch upload). Versionado de documentos. Soporte multi-idioma en extracción de texto. |
| **Cumplimiento** | Reportes automáticos de auditoría (GDPR, SOC2). Dashboards de compliance. Firma electrónica de documentos. |
| **Multi-tenant (visión)** | Aislamiento a nivel de organización (`tenant_id` en shared schema + middleware Zero-Trust que falla si falta el claim). El enforcement real actual es por departamento (RBAC + M2M `user_department` + filtro en `execute_query`) — el aislamiento interno ya está implementado y verificado. |
| **Agentes IA** | Pipeline multi-agente: Planner (basado en reglas, conserva el determinismo de las capas pre-IA) → Executor (build) → Reviewer (re-check anti-alucinación). |
| **Ingesta externa** | Conectores configurables por admin (Confluence, Notion, repos GitHub) asociados a un `department_id` — respetan el mismo filtro RBAC. Ingestión incremental. |
| **Identidad** | OAuth2 / OIDC para SSO (Google, Active Directory) sobre el bearer JWT actual. |
| **Pruebas de carga** | Smoke/load testing de rendimiento (latencia, concurrencia, throughput RAG). |

---

## h. Pilares de Diseño y Garantía de Calidad

| Pilar | Aplicación en el Proyecto |
|---|---|
| **Arquitectura Limpia** | Clean Architecture con separación nítida controller/servicio/infraestructura. Dependency Injection mediante FastAPI `Depends`. Monolito modular desacoplado. |
| **Seguridad en Profundidad** | JWT + Argon2id para autenticación. RBAC por departamento con validación en cada operación. Zero-Trust network (PostgreSQL y Ollama sin puertos expuestos al host). SHA-256 en memoria. AuditLog inmutable con trigger `REJECT`. Fail-closed ante cualquier error de validación. |
| **Privacidad por Diseño** | Inferencia 100% local con Ollama: los datos nunca abandonan la infraestructura del cliente. Aislamiento departamental: cada rol solo accede a los documentos de su departamento. Sin telemetría externa ni dependencia de APIs cloud. |
| **Calidad y Testing** | TDD estricto (RED → GREEN → REFACTOR) en cada hito. Tests unitarios + HTTP + integración. Cobertura mínima > 70%. Ruff (lint + format) en pre-commit. Pipeline CI con ruff, pytest, bandit y pip-audit en GitHub Actions. |
| **Portabilidad y Despliegue** | Docker Compose single-command (`docker compose up --build`). Entorno productivo replicable con `docker compose -f docker-compose.prod.yml`. Agnóstico de proveedor: cualquier VPS que cumpla los requisitos mínimos (tabla en sección `e`). |
| **Costo Cero en Inferencia** | Sin costes por token, llamadas API ni suscripciones cloud. El modelo Qwen2.5 se ejecuta íntegramente en hardware local. Ideal para startups, entornos regulados y presupuestos ajustados. |
| **Observabilidad** | Logging JSON estructurado con `request_id` de correlación. Access log middleware registra `method`, `path`, `status`, `latency_ms`. Health endpoint con `version`, `uptime`, `request_id`. Graceful shutdown. Preparado para OpenTelemetry. |
| **Mantenibilidad** | Conventional commits en cada entrega. Pre-commit hooks (lint + tests). Type hints estrictos en toda la base de código. Imports explícitos (sin wildcards). Documentación viva sincronizada (README + SPEC + SECURITY). |


---

## i. CI/CD y DevSecOps

El pipeline aplica calidad, seguridad y despliegue sobre cada push a `main`. Gates antes de que el código llegue a producción:

```mermaid
graph LR
    A[git push] --> B[GitHub Actions]
    B --> C[quality<br/>ruff check + format]
    B --> D[test<br/>pytest + coverage]
    B --> E[security<br/>bandit + pip-audit]
    C --> F{build}
    D --> F
    E --> F
    F --> G[docker build]
    G --> H[deploy]
    H --> I[VPS<br/>Docker Compose + Caddy HTTPS]

    style A fill:#1f77b4,stroke:#fff,color:#fff
    style B fill:#ff7f0e,stroke:#fff,color:#fff
    style C fill:#2ca02c,stroke:#fff,color:#fff
    style D fill:#2ca02c,stroke:#fff,color:#fff
    style E fill:#d62728,stroke:#fff,color:#fff
    style F fill:#ff7f0e,stroke:#fff,color:#fff
    style G fill:#9467bd,stroke:#fff,color:#fff
    style H fill:#1f77b4,stroke:#fff,color:#fff
    style I fill:#2ca02c,stroke:#fff,color:#fff
```

**Gates del pipeline:**

| Gate | Herramienta | ¿Qué detecta? |
|---|---|---|
| **Lint** | Ruff | Errores de sintaxis, imports no usados, violaciones de estilo |
| **Formato** | Ruff | Inconsistencias de formato (single source of truth) |
| **Tests** | Pytest (273 tests) | Regresiones funcionales, cobertura > 70% |
| **SAST** | Bandit | Hardcoded secrets, SQLi, inyecciones, malas prácticas |
| **Deps** | pip-audit | CVEs conocidos en dependencias (advertido, no bloqueante) |
| **Build** | Docker | Verifica que la imagen compila y el Dockerfile es válido |
| **Deploy** | SSH + Docker Compose | Despliegue real verificado en VPS con HTTPS + TLS (Let's Encrypt). |

### Seguridad en el pipeline (DevSecOps)

- **SAST (Static Application Security Testing)**: Bandit escanea `src/` en busca de vulnerabilidades de código. Se ejecuta en cada push.
- **Dependency scanning**: pip-audit compara `requirements.txt` contra bases de datos de CVEs. Detecta librerías con vulnerabilidades conocidas.
- **Secretos**: Las credenciales de producción se inyectan vía GitHub Secrets (`VPS_HOST`, `VPS_SSH_KEY`, etc.). Nunca están en el repositorio.

### Shift-Left local

```bash
# Antes de hacer push, ejecuta localmente el mismo check que el CI:
nexus.py check    # ruff check → ruff format --check → pytest
```

---

## Metodología TDD (RED → GREEN → REFACTOR)

1. **RED:** Escribir test primero → ejecutar → debe fallar
2. **GREEN:** Implementar código mínimo para pasar el test
3. **REFACTOR:** Mejorar el código manteniendo tests verdes

---
## Quick Start (evaluación del TFM)

```bash
# 1. Iniciar el ecosistema completo
nexus.py dev

# 2. Obtener token JWT (admin)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 3. Subir un documento PDF
nexus.py upload ruta/a/documento.pdf --department-id 1 --token "$TOKEN"

# 4. Listar documentos
nexus.py document list --token "$TOKEN"

# 5. Abrir interfaz web
start http://localhost:8000        # Windows
# open http://localhost:8000       # macOS
# xdg-open http://localhost:8000   # Linux

# 6. Consulta RAG (vía API)
curl -s -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"¿Qué documentos hay sobre seguridad?","document_ids":[1,2]}'
```

---

## Checklist Final

```bash
nexus dev       # levantar entorno
nexus test      # ejecutar tests (pytest -v)
nexus cov       # reporte de cobertura
pre-commit install                    # hooks pre-commit (lint + format)
pre-commit install --hook-type pre-push  # hook pre-push (tests)
```

---

## j. Evaluación — Cómo probar el proyecto

### Opción 1 (recomendada): Docker local

```bash
# Requisito: Docker + Docker Compose instalados
git clone https://github.com/agado/khora-nexus-insight.git
cd khora-nexus-insight
cp .env.example .env
docker compose up --build
```

> ⚠️ Edita `.env` antes de arrancar: personaliza `JWT_SECRET` (desarrollo) o `PROD_JWT_SECRET` (producción). El valor por defecto es inseguro y en producción la app no arrancará.

### Opción 2: GitHub Codespaces (gratuito, sin instalación local)

1. Ir a `https://github.com/agado/khora-nexus-insight`
2. Botón verde **Code** → **Codespaces** → **Create codespace on main**
3. Esperar a que se configure el entorno (2-3 minutos)
4. En la terminal del codespace: `docker compose up --build`
5. Abrir el puerto 8000 (Codespaces muestra un aviso automático)

### Opción 3: Despliegue en VPS (producción)

El proyecto incluye pipeline CI/CD y despliegue real en un VPS que cumpla los requisitos mínimos (tabla en sección `e`):

1. Ejecutar `scripts/setup-vps.sh` en el servidor.
2. Preparar `.env` (ver tabla abajo) y abrir puertos 80/443.
3. `docker compose -f docker-compose.prod.yml up -d --build` (o activar el CD de GitHub Actions añadiendo los secrets del VPS).

#### Preparación pre-deploy del `.env`

El único artefacto de configuración del despliegue es `.env` (creado por `setup-vps.sh` desde `.env.example`). Antes del primer arranque personaliza estas variables:

| Variable | Requerida | Cómo obtener el valor |
|---|---|---|
| `PROD_JWT_SECRET` | ✅ | Generar con `openssl rand -base64 48` (≥64 chars). Nunca el placeholder `CHANGE_ME_*`: la app no arranca (fail-closed). |
| `PROD_DB_PASSWORD` | ✅ | Generar con `openssl rand -base64 32` |
| `PROD_DB_USER` / `PROD_DB_NAME` | ✅ | Los defaults de la plantilla son válidos (`nexus_db_user` / `nexus_insight_db`) |
| `SERVER_NAME` | ✅ | Dominio real o `<IP_pública>.nip.io` (p. ej. `51.170.44.127.nip.io`). Si queda vacío, Caddy sirve HTTP sin TLS. |
| `PROD_COMPANY_NAME` | opcional | Nombre que aparece en la barra de navegación web |
| `PROD_JWT_ALGORITHM` / `PROD_JWT_EXPIRATION_MINUTES` | opcional | Defaults: `HS256` / `30` min |

`scripts/deploy.sh` valida estas variables antes de arrancar (pre-flight) y el guard anti-filtrado aborta si `.env` llegara a estar trackeado por git. Nunca comitees `.env`.

#### Despliegue seguro en Oracle Cloud (primer arranque)

Recomendado para minimizar riesgos en el arranque en producción:

1. **Cloud-init (opción más segura):** al crear la instancia (Ubuntu 22.04+, x86_64 o ARM64), pega el contenido de `scripts/setup-vps.sh` en **Advanced options → Management → Custom cloud-init script** (debe empezar por `#!/usr/bin/env bash`). El bootstrap se ejecuta solo en el primer arranque, como root y **sin depender de tu sesión SSH**.
2. **Si lo ejecutas a mano:** hazlo dentro de `tmux new -s setup` → `sudo bash setup-vps.sh`. `tmux` evita que una caída de la conexión SSH interrumpa el script a medias.
3. **Recuperación de emergencia:** si por cualquier motivo pierdes SSH, usa **OCI Console → Instancia → Console connection (VNC)**. No requiere puertos abiertos y permite recuperar el acceso.
4. **Verificación post-bootstrap:** `ufw status` (solo 22/80/443), `docker info`, y probar una **nueva** sesión SSH en otra terminal antes de cerrar la actual.

> Gotchas de red de OCI y operativa de producción (rollback, restauración y validación post-deploy) en [`docs/DEPLOY_OCI.md`](./docs/DEPLOY_OCI.md).

#### Primer uso (primer click)

Con el despliegue verificado, el primer acceso a la aplicación es:

1. **Recuperar la contraseña de `admin`** (generada por `setup-vps.sh`, nunca en el repo):
   ```bash
   cat /opt/nexus-insight/secrets/admin_password.txt
   ```
2. Abrir `https://<SERVER_NAME>` — el valor de `SERVER_NAME` de tu `.env` (redirige a `/login`).
3. Iniciar sesión con el usuario `admin` y la contraseña del paso 1.
4. En el panel, pulsar **Subir** y adjuntar un PDF de ejemplo.
5. Pulsar **Consultar** y hacer una pregunta sobre ese documento: la respuesta llega adaptada al rol del receptor (filtrado dual: departamento + tono).

### Opción 4: Demo desplegada (URL para el corrector)

Instancia real de evaluación en Oracle Cloud: `https://51.170.44.127.nip.io`

---

## k. Presentación y vídeo demo

* **Slides:** [`https://agado.github.io/khora-nexus-insight/slides.html`](https://agado.github.io/khora-nexus-insight/slides.html) — presentación pública del proyecto (el archivo también se entrega en `docs/slides.html` del repositorio).
* **Vídeo explicativo:** [`https://youtu.be/wtJXqm6RAVc`](https://youtu.be/wtJXqm6RAVc) — explicación del proyecto con captura de pantalla del sistema en funcionamiento.

---

## Licencia

**All Rights Reserved.** Copyright © 2026 Khora Nexus Insight.  
Este proyecto es parte de un Trabajo de Fin de Máster (TFM). No está licenciado para uso público sin autorización expresa. Consulte el archivo [LICENSE](./LICENSE) para más información.