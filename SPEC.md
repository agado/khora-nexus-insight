# SPEC.md — Especificación Técnica del Backend Nexus Insight

## 1. Propósito del documento
Este documento define el contrato técnico y arquitectónico del backend de **Nexus Insight**. Describe de forma vinculante los endpoints, modelos de datos, reglas de negocio, flujos internos y restricciones de seguridad que rigen el sistema. 

Es la referencia principal para el desarrollo, la suite de pruebas y las auditorías del tribunal, garantizando que el software cumpla estrictamente con los paradigmas de **Specification-Driven Development (SDD)**, **Test-Driven Development (TDD)** y **Secure Software Development Life Cycle (SSDLC)**. Cada decisión técnica aquí recogida se alinea con los pilares de diseño del proyecto (Arquitectura Limpia, Seguridad en Profundidad, Privacidad por Diseño, Portabilidad, Costo Cero y Observabilidad), detallados en el `README.md`.

---

## 2. Arquitectura General del Backend
El sistema está diseñado bajo un enfoque de **Monolito Modular** y se ejecuta de manera aislada dentro de un contenedor Docker. 

Para mitigar vectores de ataque y garantizar el aislamiento perimetral, el backend es el **único** punto de acceso con capacidad de comunicación hacia los servicios periféricos a través de la red interna privada `nexus-network`:
* **PostgreSQL:** Motor de persistencia relacional asíncrono.
* **Ollama:** Servidor local de inferencia para el motor de IA.

---

## 3. Módulos Principales

### 3.1 Capa de API (FastAPI)
* Enrutadores completamente versionados bajo el prefijo `/api/v1/`.
* Control de ciclo de vida asíncrono de las peticiones mediante Uvicorn.
* Inyección de dependencias nativa para validación de contratos de entrada/salida.

### 3.2 Capa Core (Núcleo)
* **Configuración:** Gestión centralizada y tipada de variables de entorno mediante `Pydantic Settings`.
* **Persistencia:** Conexión y *pooling* asíncrono a PostgreSQL utilizando `SQLAlchemy 2.0` y el driver `asyncpg`.
* **Seguridad:** Proveedor de identidad local con firmado/verificación de tokens JWT (`src/core/auth/jwt.py` → HS256) y hasheo Argon2id (`src/core/auth/security.py`).
* **Servicios:** Lógica de autenticación desacoplada en `src/core/services/auth_service.py` (Clean Architecture: endpoint → servicio → infraestructura).

### 3.3 Motor de IA Local (Ollama)
* Inferencia local dedicada utilizando el modelo **`qwen2.5:1.5b`**.
* Consumo exclusivo por HTTP desde el backend mediante endpoints internos del contenedor.

### 3.4 Subsistema de Auditoría
* Registro síncrono e inmutable de tipo *Append-Only*.
* Implementación de triggers a nivel de base de datos para interceptar y **bloquear de forma absoluta** sentencias `UPDATE` o `DELETE`.

---

## 4. Modelos de Datos (Esquemas de Persistencia)

### 4.0 Entidad: Department
```typescript
Department {
    id: int                         // Clave primaria autoincremental
    name: str                       // Nombre único del departamento (IT, RRHH, PM)
}
```

### 4.1 Entidad: User
```typescript
User {
    id: int                         // Clave primaria autoincremental
    username: str                   // Identificador único de inicio de sesión
    hashed_password: str            // Hash criptográfico generado con Argon2id
    role: Literal["admin", "lead", "staff"] // Rol asignado para el control RBAC
    department_id: int              // Clave foránea -> Department.id (departamento primario)
    created_at: datetime            // Timestamp con zona horaria UTC
}
```

#### Tabla auxiliar: user_department (M2M)
```typescript
user_department {
    user_id: int         // Clave foránea -> User.id (PK compuesta)
    department_id: int   // Clave foránea -> Department.id (PK compuesta)
}
```
La relación N:M entre usuarios y departamentos permite que un usuario acceda a documentos de múltiples departamentos. El departamento primario se define en `User.department_id`. Los departamentos adicionales accesibles se almacenan en `user_department`. El JWT incluye la lista completa de IDs accesibles via `accessible_departments`.
### 4.2 Entidad: Document
```TypeScript
Document {
    id: int                         // Clave primaria autoincremental
    filename: str                   // Nombre original del archivo procesado
    sha256: str                     // Firma criptográfica única del contenido
    content_text: str               // Texto extraído para búsqueda
    department_id: int              // Clave foránea -> Department.id (hereda del uploader)
    uploaded_by: int                // Clave foránea -> User.id
    created_at: datetime            // Timestamp de ingesta en formato UTC
    is_public: bool                 // Visibilidad interdepartamental (default: false)
}```
### 4.3 Entidad: AuditLog
```TypeScript
AuditLog {
    id: int                         // Clave primaria autoincremental
    action: str                     // Identificador de la acción (ej: "upload_document")
    user_id: int                    // Clave foránea -> User.id
    timestamp: datetime             // Timestamp inmutable de la operación (UTC)
    metadata: JSON                  // Detalles adicionales estructurados del evento
}```
## 5. Especificación de Endpoints (Contrato de la API)
### 5.1 Módulo de Autenticación
* Ruta: POST /api/v1/auth/login

* Descripción: Valida las credenciales del usuario contra el hash Argon2id y emite un token de acceso de corta duración.

* Cuerpo de la Petición (Payload):

```JSON
{
  "username": "tfm_admin",
  "password": "string_password"
}```
* Respuesta Exitosa (200 OK):

```JSON
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer"
}```
* Respuestas de Error:

```JSON
// 401 Unauthorized — credenciales incorrectas
{
  "detail": "Invalid credentials"
}

// 422 Unprocessable Entity — payload inválido (campos faltantes)
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "password"],
      "msg": "Field required",
      "input": {"username": "admin"}
    }
  ]
}```
### 5.2 Módulo de Documentos
* Ruta: POST /api/v1/documents/upload

* Descripción: Ingesta de archivos PDF con validación criptográfica SHA-256 para prevenir colisiones e inyecciones de datos. El departamento de destino se hereda del JWT por defecto, o se envía explícitamente via `department_id`.

* Restricción de Acceso: Usuarios autenticados con role level >= 1 (staff, lead, admin). El departamento destino debe estar en los `accessible_departments` del token JWT (Zero-Trust).

* Cuerpo de la Petición: Multipart/Form-Data (Archivo físico PDF, campo `file`). Campo opcional `department_id` (int).

* Flujo Interno:

 * Validación de magic bytes (%PDF) y tamaño máximo (10 MB).

 * Lectura del flujo de bytes y cómputo del hash SHA-256 en memoria.

 * Verificación de duplicados por SHA-256 en la base de datos.

 * Extracción de texto mediante pypdf para habilitar consultas RAG locales.

 * Inserción de metadatos en la tabla Document.

 * Respuesta de Éxito (201 Created):

```JSON
{
  "id": 1,
  "filename": "auditoria_2026.pdf",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "department_id": 1,
  "uploaded_by": 1,
  "created_at": "2026-07-17T22:11:15.087447+00:00"
}```
* Ruta: GET /api/v1/documents/{id}

* Descripción: Recupera los metadatos de control de un documento indexado. El documento solo se devuelve si su `department_id` está en los `accessible_departments` del usuario autenticado.

* Respuesta de Éxito (200 OK):

```JSON
{
  "id": 1,
  "filename": "auditoria_2026.pdf",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "department_id": 1,
  "uploaded_by": 1,
  "created_at": "2026-07-17T22:11:15.087447+00:00"
}```
* Ruta: GET /api/v1/documents

* Descripción: Lista paginada de documentos filtrados por los `accessible_departments` del usuario autenticado. También incluye documentos marcados como `is_public=true` de otros departamentos.

* Parámetros Query: `skip` (int, default 0), `limit` (int, default 50).

* Respuesta de Éxito (200 OK):

```JSON
{
  "documents": [
    {
      "id": 1,
      "filename": "auditoria_2026.pdf",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "department_id": 1,
      "uploaded_by": 1,
      "created_at": "2026-07-17T22:11:15.087447+00:00",
      "is_public": false
    }
  ],
  "total": 1
}```
* Ruta: DELETE /api/v1/documents/{id}

* Descripción: Elimina un documento de la base de datos. Solo accesible para roles con nivel >= 2 (admin, lead). El documento debe pertenecer a un departamento accesible por el usuario.

* Restricción de Acceso: `require_min_level(2)`

* Respuesta de Éxito (200 OK):
```JSON
{
  "detail": "Document deleted"
}```
* Respuestas de Error: `403 Forbidden` (nivel insuficiente), `404 Not Found`.

* Ruta: PATCH /api/v1/documents/{id}/toggle-public

* Descripción: Cambia el estado `is_public` de un documento. Cualquier usuario autenticado con acceso al departamento del documento puede usarlo.

* Restricción de Acceso: `require_min_level(1)`

* Respuesta de Éxito (200 OK): Mismo formato que `DocumentResponse` con `is_public` actualizado.

* Respuestas de Error: `404 Not Found`.
### 5.3 Módulo RAG (Generación Aumentada por Recuperación)
* Ruta: POST /api/v1/rag/query

* Descripción: Ejecuta una consulta semántica contextualizada sobre los documentos autorizados utilizando inferencia puramente local.

* Cuerpo de la Petición:

```JSON
{
  "query": "¿Cuáles son las directrices de seguridad del tercer trimestre?",
  "document_ids": [1, 2],
  "audience": "ejecutivo"
}```
* Parámetros:
  - `query` (str, obligatorio): texto de la consulta.
  - `document_ids` (list[int], obligatorio): IDs de documentos a incluir en el contexto.
  - `audience` (str, opcional, default `"general"`): perfil de audiencia para adaptar el tono. Valores: `general`, `tecnico`, `ejecutivo`, `stakeholder`.

* Flujo Interno:

* Validación del token JWT e inyección del rol del usuario.

* Filtrado de los document_ids solicitados según los permisos del rol.

* Construcción del súper-prompt contextualizado en la capa de aplicación.

* Envío del prompt al contenedor de Ollama mediante HTTP interno.

* Registro de la consulta y consumo del modelo en AuditLog.

* Respuesta de Éxito (200 OK):

```JSON
{
  "answer": "Según el documento de auditoría, las directrices del tercer trimestre exigen...",
  "context_used": ["Fragmento extraído del documento 1...", "Fragmento del documento 2..."]
} ```

### 5.4 Interfaz CLI (Línea de Comandos)

La CLI de Nexus Insight (`nexus.py`) permite interactuar con la API desde la terminal sin necesidad del frontend web. Todos los comandos requieren un token JWT obtenido del endpoint de login.

* Comando: `nexus.py upload <filepath> --token <JWT> [--department-id <id>]`

* Descripción: Sube un documento PDF a la API. El archivo debe existir en el sistema de archivos local. El token JWT se obtiene de `POST /api/v1/auth/login`.

* Ejemplo:
```bash
nexus.py upload auditoria.pdf --department-id 1 --token "eyJ..."
# → Documento subido: id=3 filename=auditoria.pdf  SHA-256: e3b0c44...
```

* Comando: `nexus.py document get <id> --token <JWT>`

* Descripción: Recupera los metadatos de un documento por su ID. Muestra nombre, SHA-256, departamento, subido por y fecha de creación.

* Ejemplo:
```bash
nexus.py document get 3 --token "eyJ..."
# → Documento: id=3  Nombre: auditoria.pdf  SHA-256: e3b0c44...
```

* Comando: `nexus.py document list --token <JWT> [--skip <n>] [--limit <n>]`

* Descripción: Lista paginada de documentos accesibles según el departamento del usuario autenticado.

* Ejemplo:
```bash
nexus.py document list --token "eyJ..."
# → Documentos (3 en total):
# →   [3] auditoria.pdf — Depto 1 — 2026-07-18
# →   [2] manual.pdf — Depto 1 — 2026-07-17
```

* Manejo de errores: Si el servidor no está en ejecución, muestra un mensaje en español y termina con código 1. Errores HTTP (401, 404, 409, etc.) se muestran con el código y detalle devuelto por la API.

## 6. Reglas de Negocio e Invariantes del Sistema

### 6.1 Control de Acceso Basado en Roles (RBAC)
El sistema implementa una jerarquía de niveles de acceso mediante la factory `require_min_level(n)`:

| Rol | Nivel | Acceso |
|---|---|---|
| `staff` | 1 | Subida de documentos a su departamento, consultas RAG sobre sus departamentos accesibles |
| `lead` | 2 | Todo lo de staff, más acceso a endpoints de nivel 2 protegidos |
| `admin` | 3 | Acceso completo a todo el sistema, incluyendo endpoints de nivel 3 |

La función `require_min_level(n)` retorna un dependency checker de FastAPI. Si el nivel del usuario es menor que `n`, devuelve `403 Forbidden`. La función `require_role(role)` se mantiene para compatibilidad con checks de rol exacto.

* **Departamentos accesibles:** Cada usuario tiene un departamento primario (`department_id`) y puede tener departamentos adicionales via la tabla M2M `user_department`. La lista completa se inyecta en el JWT como `accessible_departments: list[int]`. Todos los endpoints de documentos filtran por esta lista (Zero-Trust).

### 6.2 Inmutabilidad de la Auditoría (Zero-Trust)
* Cada llamada a un endpoint sensible o de consumo de IA debe disparar de forma atómica e irreversible una inserción en la tabla `AuditLog`.
* La inmutabilidad está protegida a nivel de base de datos por políticas estrictas: cualquier intento de ejecutar comandos `UPDATE` o `DELETE` sobre dicha tabla devolverá una excepción nativa de PostgreSQL.

### 6.3 Seguridad y Ciclo de Vida Documental
* Ningún documento físico se guarda de forma permanente en el disco duro del backend en su estado original. El sistema parsea el contenido, extrae el texto para alimentar el contexto RAG y almacena únicamente los metadatos y firmas en la base de datos.
* El motor de Ollama jamás recibe rutas de archivos ni accesos directos al sistema de almacenamiento: se comunica exclusivamente mediante texto plano estructurado dentro del prompt inyectado.

---

## 7. Estrategia de Desarrollo Incremental y GitOps

### 7.1 Filosofía de Construcción Funcional (MVP)
Para mitigar la complejidad y asegurar la estabilidad de la arquitectura, el proyecto se ejecuta bajo una metodología incremental estricta. Cada iteración aborda una funcionalidad mínima y testeable:
* **Hito Inicial:** Despliegue de un endpoint de control (`GET /api/v1/health`) para validar que FastAPI, la inyección de dependencias y el contenedor base responden correctamente (HTTP 200).
* **Flujo de Consolidación:** No se avanza hacia una nueva fase del roadmap hasta que el desarrollo actual tenga cobertura de pruebas unitarias/integración en estado "Verde" y cumpla la definición de listo (*Definition of Done*).

### 7.2 Disciplina de Versionado en Git
Tanto los desarrolladores como los agentes de IA automatizados deben operar bajo estrictas directrices de control de versiones:
* **Commits Atómicos:** Cada confirmación de código debe representar un cambio funcional estable y aislado. Queda prohibido realizar commits masivos con múltiples responsabilidades cruzadas.
* **Historial Descriptivo:** Los mensajes de commit deben ser claros, concisos y detallar el módulo modificado siguiendo convenciones semánticas (ej. `feat(auth): ...` o `fix(database): ...`).

---

## 8. Restricciones Técnicas y de Seguridad (Hardening)
* **Aislamiento de Puertos:** En entornos productivos (`docker-compose.prod.yml`), PostgreSQL y Ollama operan con los puertos externos totalmente cerrados. No existe vector de ataque perimetral directo hacia ellos.
* **Principio de Menor Privilegio:** Los procesos internos de los contenedores Docker no se ejecutan bajo el usuario `root`. Se configuran usuarios del sistema con permisos mínimos específicos.
* **Gestión de Secretos:** Está terminantemente prohibido escribir contraseñas, claves secretas o firmas JWT hardcodeadas en las clases o módulos de Python. Toda configuración sensible se inyecta dinámicamente mediante el archivo oculto `.env`.

---

## 9. Manejo de Errores y Códigos de Respuesta

### 9.1 Códigos de Estado de Error (HTTP Exceptions)

| Código HTTP | Denominación Técnico-Semántica | Escenario de Activación |
| :--- | :--- | :--- |
| **400 Bad Request** | Error de Validación / Entrada | Datos mal formados, payloads incompletos o fallo en esquemas Pydantic. |
| **401 Unauthorized** | No Autenticado | Token JWT ausente, expirado o con firma criptográfica corrupta. |
| **403 Forbidden** | No Autorizado (RBAC) | El usuario está autenticado pero su rol no posee privilegios para la ruta. |
| **404 Not Found** | Recurso Inexistente | El identificador del documento o endpoint solicitado no existe en el sistema. |
| **500 Internal Error**| Fallo Crítico del Servidor | Excepciones imprevistas, caídas de base de datos o pérdida de red con Ollama. |

### 9.2 Mensajes de Éxito Estructurados
Las respuestas operativas exitosas deben retornar payloads informativos que confirmen la ejecución para facilitar las tareas de monitorización:
* **200 OK:** Operaciones estándar de consulta, login y lectura de datos.
* **201 Created:** Confirmación de recursos creados o persistidos (ej. documento indexado con éxito con su ID de control).

---

## 11. Decisiones Técnicas Vinculantes

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| **Upload por API** (Multipart) | Hot Folders (carpetas vigiladas) | Testeable con TestClient. El department_id se hereda del JWT, no se configura manualmente. |
| **Búsqueda textual con `ILIKE`** | ChromaDB / vectores | Suficiente para MVP. Sin contenedor extra ni embeddings. |
| **Departamento vía JWT** | El usuario elige departamento al subir | Zero-trust: el token es la fuente de verdad del rol y departamento. |
| **Prompt con delimitadores XML + sanitización `</`** | Guardrails anti-inyección completos | Capa OWASP ligera sin sobrecarga. `_sanitize()` elimina `</` de la query para evitar cierre anticipado de `<contexto>` o `<pregunta>`. |
| **Truncado de contexto a 4000 chars/doc** | Envío íntegro del documento | Previene DoS por contexto masivo. El modelo no necesita más de 4000 caracteres por documento para tareas RAG. |
| **Validación de longitud máxima de query (2000 chars)** | Sin límite | Previene abuso del prompt. Rechazo temprano con 400 Bad Request. |
| **Fail-Closed por transacciones atómicas** | Lógica manual de rollback | SQLAlchemy `commit()` maneja el rollback automáticamente si AuditLog falla. |
| **`nexus.py`** | Makefile | Portable Windows/Linux/Mac sin dependencias externas. |
| **Rollback automático en transacciones DB** | Lógica manual de rollback | `database.py` envuelve cada sesión en try/except → rollback + raise. |
| **Seed idempotente (upsert por username)** | Insert directo cada vez | Evita duplicados al re-ejecutar `nexus.py seed`. `--reset` para truncar y recrear. |
| **SQLAlchemy parametrizado** | Concatenación de strings SQL | Las queries siempre usan bind parameters. Sin riesgo de SQL injection. |
| **`argon2-cffi` directo** | `passlib[argon2]` | Librería mantenida activamente. Sin deprecation warnings. Contrato de API idéntico. |
| **Docker Secrets para admin password** | Variable de entorno directa | OWASP: la password se monta como archivo en `/run/secrets/`, no visible en `docker inspect` ni logs. |
| **Auto‑bootstrap en prod** | Seed manual post‑deploy | `docker-compose.prod.yml` ejecuta `alembic upgrade head && python -m src.core.seed` al arrancar. Un solo comando. |
| **`algorithms=["HS256"]` explícito** | Algoritmo implícito u omitido | Previene CVE-2015-9235 (algorithm confusion). Aunque el proyecto es monolito, la defensa en profundidad lo exige. |
| **Service layer para autenticación** | Lógica de auth inline en endpoint | SRP + testabilidad: `authenticate_user()` se testea sin FastAPI ni HTTP. El endpoint solo maneja HTTP, el servicio maneja el caso de uso. |
| **RBAC vía `require_role(role)` factory** | Inline `if role != "admin"` en cada endpoint | DRY + OCP: añadir protección a un nuevo endpoint solo cambia el argumento. Sin lógica repetida. |
| **Mini-test-app para tests RBAC** | Dependency overrides globales en conftest | Aislamiento total: no contamina la app real, cada suite de tests es independiente. |
| **AuditLog login diferido a H6** | AuditLog inline en login endpoint (H3) | Pareto: JSON logging cubre observabilidad ahora. La integración con AuditLog requiere el trigger inmutable de H6. |
| **Admin username configurable (env var)** | Hardcoded `"admin"` en seed.py | OWASP A7: el nombre del admin se lee de `ADMIN_USERNAME` env var. Validación de no vacío previa al seed. Misma contraseña fuerte por Docker secrets. |

---

## 10. Roadmap Técnico del SPEC (Fases Futuras y Usabilidad)

### 10.1 Interfaz de Usuario de Alta Accesibilidad (Post-MVP)
* **Nexus CLI (Rich Interface):** Desarrollo de una interfaz de línea de comandos avanzada integrada en el ecosistema Python utilizando `Typer` y `Rich` para dotar al sistema de usabilidad para perfiles no técnicos.
  * Paneles visuales de colores y tablas estructuradas para mostrar metadatos.
  * Barras de progreso animadas en tiempo real durante los procesos de ingesta e inferencia de Ollama.
  * Menús interactivos en la terminal para seleccionar los documentos a incluir en el contexto.
* **Separación de Capas:** El backend mantendrá sus controladores desacoplados, garantizando que la CLI consuma los mismos servicios internos de la aplicación que la API, sin comprometer el diseño de monolito modular.

### 10.2 Seguridad Avanzada
* Guardrails anti-prompt-injection con sanitización profunda de entradas.
* Rotación automática de claves JWT y certificados.
* Autenticación multifactor (TOTP) para administradores.
* Rate limiting por usuario y rol.

### 10.3 IA y Motor de Búsqueda
* ChromaDB para búsqueda semántica vectorial (embeddings).
* Soporte multi-modelo: selección configurable entre qwen, llama, mistral.
* OCR para documentos escaneados (Tesseract).
* Filtro de destinatario contextual: adaptación automática del tono según el rol del lector.

### 10.4 Infraestructura y Despliegue
* CI/CD con GitHub Actions (tests + lint + cobertura automáticos en cada push y PR).
* Escalado horizontal con balanceo de carga (múltiples instancias de la API).
* Despliegue cloud optimizado (AWS ECS / GCP Cloud Run / Azure ACA) con un solo comando.
* Soporte para entornos híbridos CPU/GPU en inferencia.

### 10.5 Observabilidad Corporativa
* OpenTelemetry para trazabilidad distribuida entre servicios.
* Dashboard de métricas en tiempo real (latencia, volumen de consultas, tasa de error).
* Alertas automáticas ante anomalías (subida de latencia, picos de error, caída de Ollama).
* Integración con SIEM corporativos mediante exportación estructurada de logs.

### 10.6 Experiencia de Usuario y Operaciones
* Nexus CLI completo con Typer + Rich (menús interactivos, barras de progreso, paneles de colores).
* Hot Folders: arrastrar y soltar documentos en carpetas vigiladas.
* Panel web de administración (React/Vue) para gestión visual.
* Procesamiento por lotes (batch upload de múltiples documentos).
* Políticas de retención de datos con limpieza automática programada.
* Notificaciones webhook al completar ingestiones o consultas.
* Exportación/importación de documentos y configuraciones del sistema.

### 10.7 Cumplimiento y Auditoría
* Reportes automáticos de auditoría (GDPR, SOC2, ISO 27001).
* Dashboards de compliance con visualización de accesos y roles.
* Firmado electrónico de documentos.
* Versionado de documentos con historial de cambios.

---

## Apéndice A: Comandos de inspección

### Entorno de desarrollo

#### Base de Datos (PostgreSQL)
```bash
# Ver tablas creadas
docker exec -i nexus_postgres_dev psql -U nexus_db_user -d nexus_insight_db -c "\dt"

# Ver estructura de una tabla
docker exec -i nexus_postgres_dev psql -U nexus_db_user -d nexus_insight_db -c "\d user"

# Ver datos de seed (usuarios)
docker exec -i nexus_postgres_dev psql -U nexus_db_user -d nexus_insight_db \
  -c 'SELECT u.id, u.username, u.role, d.name AS primary_dept FROM "user" u JOIN department d ON d.id = u.department_id ORDER BY u.id;'

# Ver accesos M2M
docker exec -i nexus_postgres_dev psql -U nexus_db_user -d nexus_insight_db \
  -c 'SELECT u.username, d.name AS accessible_dept FROM user_department ud JOIN "user" u ON u.id = ud.user_id JOIN department d ON d.id = ud.department_id ORDER BY u.username;'

docker exec -i nexus_postgres_dev psql -U nexus_db_user -d nexus_insight_db \
  -c "SELECT id, name FROM department ORDER BY id;"

# Conteo rápido
docker exec -i nexus_postgres_dev psql -U nexus_db_user -d nexus_insight_db -c "SELECT count(*) FROM \"user\";"
```

#### Backend (FastAPI)
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Logs en tiempo real
docker logs nexus_backend_dev -f
```

#### Ollama
```bash
# Logs en tiempo real
docker logs nexus_ollama_dev -f

# Verificar que el modelo está descargado
docker exec -i nexus_ollama_dev ollama list
```

#### CLI (Nexus Insight)
```bash
# Login y obtención de token JWT
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Subir documento PDF
nexus.py upload ruta/documento.pdf --department-id 1 --token "$TOKEN"

# Consultar metadatos de un documento
nexus.py document get 1 --token "$TOKEN"

# Listar documentos accesibles
nexus.py document list --token "$TOKEN"

# Listar con paginación
nexus.py document list --skip 0 --limit 10 --token "$TOKEN"
```

---

### Entorno de producción

#### Base de Datos (PostgreSQL)
```bash
# Ver tablas creadas
docker exec -i nexus_postgres psql -U nexus_db_user -d nexus_insight_db -c "\dt"

# Ver estructura de una tabla
docker exec -i nexus_postgres psql -U nexus_db_user -d nexus_insight_db -c "\d user"

# Ver datos de seed (usuarios)
docker exec -i nexus_postgres psql -U nexus_db_user -d nexus_insight_db \
  -c 'SELECT u.id, u.username, u.role, d.name AS primary_dept FROM "user" u JOIN department d ON d.id = u.department_id ORDER BY u.id;'

# Ver accesos M2M
docker exec -i nexus_postgres psql -U nexus_db_user -d nexus_insight_db \
  -c 'SELECT u.username, d.name AS accessible_dept FROM user_department ud JOIN "user" u ON u.id = ud.user_id JOIN department d ON d.id = ud.department_id ORDER BY u.username;'

docker exec -i nexus_postgres psql -U nexus_db_user -d nexus_insight_db \
  -c "SELECT id, name FROM department ORDER BY id;"

# Conteo rápido
docker exec -i nexus_postgres psql -U nexus_db_user -d nexus_insight_db \
  -c "SELECT count(*) FROM \"user\";"
```

#### Backend (FastAPI)
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Logs en tiempo real
docker logs nexus_backend -f
```

#### Ollama
```bash
# Logs en tiempo real
docker logs nexus_ollama -f

# Verificar que el modelo está descargado
docker exec -i nexus_ollama ollama list
```

---

### Persistencia de datos
```bash
# Los datos persisten entre reinicios normales:
nexus.py prod         # primer arranque → migration + seed (crea admin)
<pausa>
nexus.py down         # detiene contenedores → conserva volúmenes
nexus.py prod         # segundo arranque → seed idempotente (no duplica admin)
# Los datos están intactos: departments, users, documents, audit_logs
```

### Factory reset (volver a estado de fábrica)
```bash
# Opción A (segura): solo borra datos de seed, mantiene estructura
docker exec -i nexus_backend python -m src.core.seed --reset

# Opción B (destructiva): borra TODOS los datos y volúmenes
docker compose -f docker-compose.prod.yml down -v
nexus.py prod   # fresh start: migration + seed admin desde cero
```