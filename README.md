# Nexus Insight

![Python 3.13](https://img.shields.io/badge/python-3.13-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![Docker](https://img.shields.io/badge/docker_compose-single--command-2496ED?logo=docker)
![Tests](https://img.shields.io/badge/tests-190%2B-green)
![RAG](https://img.shields.io/badge/RAG-100%25_local-7B1FA2?logo=ollama)
![License](https://img.shields.io/badge/license-All_Rights_Reserved-red)
[![Conventional Commits](https://img.shields.io/badge/conventional%20commits-1.0.0-FE5196?logo=conventionalcommits)](https://conventionalcommits.org)

**Inferencia RAG 100% local, Zero-Trust, multi-departamento. Sin APIs cloud, sin costes por token, sin fugas de datos.**

Nexus Insight es un backend de análisis documental inteligente que permite a organizaciones en sectores regulados (banca, salud, administración pública, investigación) desplegar un asistente GenAI sobre su propia documentación técnica y estratégica — sin que un solo byte salga de su infraestructura.

El core del producto es su **Dual-Layer Filtering**: (1) aislamiento departamental estricto por RBAC + Zero-Trust network, y (2) adaptación cognitiva del output según el rol del destinatario (técnico, directivo, PM, legal). Todo sobre un modelo local Qwen2.5 1.5B vía Ollama, sin depender de OpenAI, Anthropic ni ninguna API externa.

**Para quién:** CISO que necesita decir "sí" a la IA sin perder el sueño. PM que quiere traducir documentación técnica en insights estratégicos. Startups que no pueden permitirse costes de API. Universidades que manejan investigación patentable.

## a. Descripción general del proyecto

<details> <summary>Descripción para técnicos (por defecto)</summary>

Nexus Insight es una plataforma de análisis documental inteligente diseñada bajo el paradigma Zero ‑Trust y una arquitectura monolito modular. Su objetivo es permitir la ingesta, procesamiento e inferencias RAG 100% locales, garantizando que la información confidencial nunca abandone la infraestructura física del cliente.

La IA se ejecuta en un contenedor aislado dentro de una red interna de Docker, cumpliendo los requisitos de soberanía de datos y seguridad corporativa.

Puntos clave para técnicos:

Seguridad y soberanía: Arquitectura y ejecución local para máxima privacidad. Las variables de entorno usan el prefijo `NEXUS_` para evitar colisiones con otras aplicaciones.

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
* Base de datos: PostgreSQL 15 + SQLAlchemy 2.0 (async con asyncpg).
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
git clone https://github.com/tu-org/nexus-insight.git
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

> También disponible via `python nexus.py dev` en cualquier OS.

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

Bloque corregido para evitar errores de interpretación en OpenCode.

nexus-insight/
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── .env
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── pytest.ini
├── requirements.txt
├── agents.md
├── ruff.toml
├── SECURITY.md                     ← invariantes de seguridad
├── SPEC.md
├── migrations/                     ← migraciones Alembic
│   └── versions/
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
│   │   ├── services/                ← use cases (business logic)
│   │   └── storage/                 ← file I/O
├── templates/                        ← Jinja2 templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── _upload_form.html
│   ├── _user_form.html               ← crear usuario con validación pw
│   ├── _user_list.html
│   ├── _query_form.html
│   ├── _query_result.html
│   └── _document_list.html
├── static/
│   └── css/
│       └── theme.css
└── tests/                           ← refleja src/
    ├── conftest.py
    ├── api/
    │   └── v1/
    └── core/
        └── services/


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

El sistema implementa un perímetro de seguridad donde los servicios de persistencia e inferencia están completamente aislados del exterior. La API de FastAPI actúa como el único punto de entrada autorizado.

```mermaid
flowchart TB
    subgraph Internet / Host Local [Zona Externa - No Segura]
        User([Cliente / Usuario]) -- HTTP Request <br> Puerto 8000 --> API
    end

    subgraph Docker_Network [Red Interna Privada: nexus-network]
        API[Backend FastAPI <br> Puerto 8000] 
        DB[(PostgreSQL DB <br> Puerto 5432)]
        Ollama[Servidor Ollama <br> Puerto 11434]

        %% Flujos Internos Seguros
        API -- 1. Consulta/Persiste <br> SSL Interno --> DB
        API -- 2. Contexto Inyectado <br> HTTP Interno --> Ollama
    end

    %% Bloqueos y Aislamiento (Representación de Seguridad)
    Internet -.->|BLOQUEADO <br> Sin Puertos Expuestos| DB
    Internet -.->|BLOQUEADO <br> Sin Puertos Expuestos| Ollama
    Ollama -.->|BLOQUEADO <br> Sin Acceso Directo| DB

    %% Estilos Visuales
    style API fill:#1f77b4,stroke:#fff,stroke-width:2px,color:#fff
    style DB fill:#2ca02c,stroke:#fff,stroke-width:2px,color:#fff
    style Ollama fill:#9467bd,stroke:#fff,stroke-width:2px,color:#fff
    style Docker_Network fill:#f9f9f9,stroke:#333,stroke-dasharray: 5 5
```


#### Pilares del Diseño de Seguridad y Soberanía de Datos

Este modelo arquitectónico soluciona de raíz los riesgos de filtración de datos y ataques perimetrales mediante tres principios de diseño:

* **Soberanía de Datos Absoluta (Inferencia 100% Local):**
    * **Consumo sin fugas:** A diferencia de las APIs comerciales (OpenAI, Anthropic), el procesamiento del modelo `qwen2.5:1.5b` ocurre de forma confinada dentro del contenedor local de **Ollama** (`ollama/ollama:latest`).
    * **Sin telemetría externa:** Ni los datos del usuario, ni los fragmentos de los documentos inyectados en el contexto, ni los prompts de consulta viajan por internet ni son compartidos para entrenar modelos externos.
* **Aislamiento de Red Zero-Trust (Cortafuegos Perimetral):**
    * **Invisibilidad de servicios:** PostgreSQL (puerto `5432`) y Ollama (puerto `11434`) operan en la red virtual privada `nexus-network` **sin mapear o exponer puertos hacia el host exterior**. Son invisibles ante escaneos de puertos en la máquina física.
    * **Punto único de acceso:** El backend de FastAPI actúa como el único perímetro autorizado (puerto `8000`). Ningún comando externo puede interactuar directamente con la base de datos o con el motor de IA sin ser interceptado por el middleware de validación criptográfica (JWT) y el control de accesos (RBAC).
* **Modularidad Operativa (Acoplamiento Suelto):**
    * **Independencia de servicios:** La infraestructura está diseñada para permitir el encendido, apagado o actualización de cada máquina por separado (`docker compose up <servicio>`). 
    * **Fácil mantenimiento:** Si se requiere aislar Ollama por mantenimiento, actualizar a una versión más segura o auditar la base de datos de manera aislada, el ecosistema lo permite sin comprometer la integridad o la estabilidad del resto de módulos del backend.

## f. Usuario y contraseña de prueba

* Credenciales de desarrollo incluidas en `.env.example`:

| Usuario | Rol | Departamento | Acceso a departamentos | Contraseña |
|---|---|---|---|---|
| `admin` | admin | IT | IT + RRHH + PM | `admin123` |
| `lead_it` | lead | IT | IT | `lead123` |
| `lead_hr` | lead | RRHH | RRHH | `lead123` |
| `lead_pm` | lead | PM | PM | `lead123` |
| `staff_it` | staff | IT | IT | `staff123` |
| `staff_hr` | staff | RRHH | RRHH | `staff123` |
| `staff_pm` | staff | PM | PM | `staff123` |
| **`ceo`** | **admin** | **IT** | **IT + RRHH + PM** | `ceo123` |

Jerarquía de roles: `admin` (nivel 3) > `lead` (nivel 2) > `staff` (nivel 1).

(Nunca usar estas credenciales en producción.)



> Historial completo de versiones en [`CHANGELOG.md`](./CHANGELOG.md).

## g. Roadmap de Desarrollo (TDD)

| Hito | Objetivo | Criterio de Aceptación (DoD) |
|---|---|---|---|
| **H1** ✅ | Scaffolding: Docker, FastAPI, health endpoints | `GET /api/v1/health` responde 200. 13 tests. |
| **H2** ✅ | `nexus.py`, base de datos, migraciones Alembic, modelos (`+department_id`), seed, test integración DB, `pytest-cov` | `nexus dev` funciona. Tablas creadas. Seed poblado. |
| **H3** ✅ | Autenticación JWT + Argon2id + middleware RBAC | Login OK → 200. Sin token → 401. Prohibición por rol → 403. |
| **H4** ✅ | Ingesta documental por API + frontend web + CLI: SHA-256, extracción texto (pypdf), búsqueda textual, roles (admin/lead/staff), departamentos M2M, login web, dashboard, upload, lista documentos, logout, CLI upload/get/list | Upload → 200/409. 167 tests. Frontend funcional. CLI funcional. |
| **H5** ✅ | Motor RAG: consulta con filtro RBAC, contexto a Ollama, delimitadores XML anti-inyección + sanitización OWASP, truncado de contexto a 4K chars, endpoint API + frontend web + CLI | `POST /api/v1/rag/query` → 200. 186 tests. Frontend Consultar funcional. |
| **H6** ✅ | Auditoría y trazabilidad: Alembic, trigger PostgreSQL inmutable, AuditLog completo, visor Registros | Ver detalle abajo ↓ |
| **H7** ✅ | Ciclo de vida documental: borrar docs, is\_public, CRUD usuarios, export .txt, CLI query | Ver detalle abajo ↓ |
| **H8** ✅ | Experiencia corporativa: mejora visual, adaptación de tono por departamento/stakeholder, administración de usuarios | Ver detalle abajo ↓ |
| **H9** ✅ | Seguridad: rate limiting (login 5/min), CSP + security headers, password complexity policy | Ver detalle abajo ↓ |

### H6 — Auditoría y trazabilidad

| Código | Objetivo | Criterio de Aceptación |
|--------|----------|------------------------|
| **H6.1** | Alembic funcional + migration trigger inmutable en audit_log | `alembic upgrade head` crea tablas + trigger. Rollback funcional. |
| **H6.2** | AuditLog en login/upload/delete + visor Registros en frontend | Login, subida y borrado → fila en audit_logs. Pestaña Registros muestra tabla paginada. |

### H7 — Ciclo de vida documental

| Código | Objetivo | Criterio de Aceptación |
|--------|----------|------------------------|
| **H7.1** | Borrar documentos (admin/lead) + staff sin subir | `DELETE /api/v1/documents/{id}` → 200/404/403. Botón frontend. |
| **H7.2** | Documento de acceso general (`is_public`) | Columna. Bypass del filtro departamental en listado + RAG. |
| **H7.3** ✅ | CRUD usuarios (admin) | Alta/baja/modificación de usuarios desde frontend. API completa. 34 tests. |
| **H7.4** | Exportar respuesta .txt + CLI query | Botón en consulta. `nexus.py query` funcional. |

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

### H8 — Experiencia corporativa

| Código | Objetivo | Criterio de Aceptación |
|--------|----------|------------------------|
| **H8.1** ✅ | Mejora visual (tema Pico CSS, logo, tipografía) | Aspecto corporativo, coherente con la marca. 0 inline styles. |
| **H8.2** ✅ | Adaptación de tono por departamento/stakeholder | Selector de audiencia en consulta. El prompt se adapta automáticamente. |
| **H8.3** ✅ | Administración de usuarios (web) | Lista, crear, editar, eliminar, resetear contraseña desde pestaña Usuarios. Navegación HTMX dentro del tab. Feedback visual con toasts. Validación OWASP (rol, departamentos accesibles, unicidad). Auditoría de cada acción. |

### Post-MVP (Futuro)

| Dimensión | Mejora prevista |
|---|---|
| **Seguridad** | Guardrails anti-prompt-injection completos. Rotación automática de claves JWT. Autenticación multifactor (TOTP). Rate limiting por usuario. |
| **IA y Búsqueda** | ChromaDB para búsqueda semántica vectorial. Multi-modelo (selección configurable entre qwen, llama, mistral). OCR para documentos escaneados. |
| **Infraestructura** | CI/CD con GitHub Actions (tests + lint + cobertura automáticos). Escalado horizontal con balanceo de carga. Despliegue en cloud (AWS/GCP/Azure) con un solo comando. |
| **Observabilidad** | OpenTelemetry para trazabilidad distribuida. Dashboard de métricas en tiempo real (latencia, consultas, errores). Alertas automáticas. |
| **UX** | Nexus CLI completo con Typer + Rich (menús interactivos, barras de progreso, colores). Hot Folders para arrastrar y soltar documentos. Panel web de administración (React/Vue). |
| **Operaciones** | Políticas de retención de datos (limpieza automática). Exportación/importación de documentos y configuraciones. Notificaciones webhook al completar procesos. |
| **Ingesta** | Procesamiento por lotes (batch upload). Versionado de documentos. Soporte multi-idioma en extracción de texto. |
| **Cumplimiento** | Reportes automáticos de auditoría (GDPR, SOC2). Dashboards de compliance. Firma electrónica de documentos. |

---

## h. Pilares de Diseño y Garantía de Calidad

| Pilar | Aplicación en el Proyecto |
|---|---|
| **Arquitectura Limpia** | Clean Architecture con separación nítida controller/servicio/infraestructura. Dependency Injection mediante FastAPI `Depends`. Monolito modular desacoplado. |
| **Seguridad en Profundidad** | JWT + Argon2id para autenticación. RBAC por departamento con validación en cada operación. Zero-Trust network (PostgreSQL y Ollama sin puertos expuestos al host). SHA-256 en memoria. AuditLog inmutable con trigger `REJECT`. Fail-closed ante cualquier error de validación. |
| **Privacidad por Diseño** | Inferencia 100% local con Ollama: los datos nunca abandonan la infraestructura del cliente. Aislamiento departamental: cada rol solo accede a los documentos de su departamento. Sin telemetría externa ni dependencia de APIs cloud. |
| **Calidad y Testing** | TDD estricto (RED → GREEN → REFACTOR) en cada hito. Tests unitarios + HTTP + integración. Cobertura mínima > 70%. Ruff (lint + format) en pre-commit. |
| **Portabilidad y Despliegue** | Docker Compose single-command (`docker compose up --build`). Entorno productivo replicable con `docker compose -f docker-compose.prod.yml`. Portable a cualquier proveedor cloud (AWS ECS, GCP Cloud Run, Azure ACA) sin cambios arquitectónicos. |
| **Costo Cero en Inferencia** | Sin costes por token, llamadas API ni suscripciones cloud. El modelo Qwen2.5 se ejecuta íntegramente en hardware local. Ideal para startups, entornos regulados y presupuestos ajustados. |
| **Observabilidad** | Logging JSON estructurado en stdout para cada request (autorizado y denegado). Preparado para OpenTelemetry (trazabilidad distribuida). Dashboard de métricas planificado en Post-MVP. |
| **Mantenibilidad** | Conventional commits en cada entrega. Pre-commit hooks (lint + tests). Type hints estrictos en toda la base de código. Imports explícitos (sin wildcards). Documentación viva sincronizada (README + SPEC + SECURITY). |


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

### Opción 3: Despliegue cloud (futuro)

Servicios como **Railway**, **Render** o **Fly.io** tienen capas gratuitas suficientes. Pendiente de evaluación.

---

## i. Presentación y Vídeo Demo

### Slides
- **Formato:** HTML interactivo (reveal.js) con estilo corporativo
- **Archivo:** [`docs/slides.html`](./docs/slides.html) — abrir en navegador, navegar con ← →
- **URL pública:** (pendiente de publicar — Google Slides, Canva o similar)

### Vídeo Demo
- **Guión:** [`docs/VIDEO_SCRIPT.md`](./docs/VIDEO_SCRIPT.md) — desglose por escenas con timings y narración
- **Duración estimada:** 5–7 minutos
- **URL pública:** (pendiente de grabar y publicar — YouTube, Drive o similar)

---
## Licencia

**All Rights Reserved.** Copyright © 2026 Khora Nexus Insight.  
Este proyecto es parte de un Trabajo de Fin de Máster (TFM). No está licenciado para uso público sin autorización expresa. Consulte el archivo [LICENSE](./LICENSE) para más información.