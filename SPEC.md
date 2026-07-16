# SPEC.md — Especificación Técnica del Backend Nexus Insight

## 1. Propósito del documento
Este documento define el contrato técnico y arquitectónico del backend de **Nexus Insight**. Describe de forma vinculante los endpoints, modelos de datos, reglas de negocio, flujos internos y restricciones de seguridad que rigen el sistema. 

Es la referencia principal para el desarrollo, la suite de pruebas y las auditorías del tribunal, garantizando que el software cumpla estrictamente con los paradigmas de **Specification-Driven Development (SDD)**, **Test-Driven Development (TDD)** y **Secure Software Development Life Cycle (SSDLC)**.

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
* **Seguridad:** Proveedor de identidad local encargado del firmado/verificación de tokens JWT y del hasheo de alta seguridad con **Argon2id**.

### 3.3 Motor de IA Local (Ollama)
* Inferencia local dedicada utilizando el modelo **`qwen2.5:1.5b`**.
* Consumo exclusivo por HTTP desde el backend mediante endpoints internos del contenedor.

### 3.4 Subsistema de Auditoría
* Registro síncrono e inmutable de tipo *Append-Only*.
* Implementación de triggers a nivel de base de datos para interceptar y **bloquear de forma absoluta** sentencias `UPDATE` o `DELETE`.

---

## 4. Modelos de Datos (Esquemas de Persistencia)

### 4.1 Entidad: User
```typescript
User {
    id: int                         // Clave primaria autoincremental
    username: str                   // Identificador único de inicio de sesión
    hashed_password: str            // Hash criptográfico generado con Argon2id
    role: Literal["admin", "staff"] // Rol asignado para el control RBAC
    created_at: datetime            // Timestamp con zona horaria UTC
}
```
### 4.2 Entidad: Document
```TypeScript
Document {
    id: int                         // Clave primaria autoincremental
    filename: str                   // Nombre original del archivo procesado
    sha256: str                     // Firma criptográfica única del contenido
    uploaded_by: int                // Clave foránea -> User.id
    created_at: datetime            // Timestamp de ingesta en formato UTC
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
### 5.2 Módulo de Documentos
* Ruta: POST /api/v1/documents/upload

* Descripción: Ingesta de archivos con validación criptográfica para prevenir colisiones e inyecciones de datos.

* Restricción de Acceso: Exclusivo para rol admin.

* Cuerpo de la Petición: Multipart/Form-Data (Archivo físico TXT/PDF).

* Flujo Interno:

 * Lectura del flujo de bytes y cómputo del hash SHA-256 en memoria.

 * Verificación de duplicados en la base de datos.

 * La ingesta documental incluye extracción de texto mediante pypdf para habilitar consultas RAG locales.

 * Extracción de texto e inserción de metadatos.

 * Generación síncrona del registro en AuditLog.

 * Respuesta de Éxito (201 Created):

```JSON
{
  "document_id": 1,
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}```
* Ruta: GET /api/v1/documents/{id}

* Descripción: Recupera los metadatos de control de un documento indexado.

* Respuesta de Éxito (200 OK):

```JSON
{
  "id": 1,
  "filename": "auditoria_2026.txt",
  "sha256": "e3b0c44298fc...",
  "uploaded_by": 1
}```
### 5.3 Módulo RAG (Generación Aumentada por Recuperación)
* Ruta: POST /api/v1/rag/query

* Descripción: Ejecuta una consulta semántica contextualizada sobre los documentos autorizados utilizando inferencia puramente local.

* Cuerpo de la Petición:

```JSON
{
  "query": "¿Cuáles son las directrices de seguridad del tercer trimestre?",
  "document_ids": [1, 2]
}```
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

## 6. Reglas de Negocio e Invariantes del Sistema

### 6.1 Control de Acceso Basado en Roles (RBAC)
* **`admin`:** Posee privilegios totales sobre el ecosistema. Es el único perfil habilitado para realizar ingesta de nuevos documentos, consultar logs del sistema, alterar configuraciones y ejecutar consultas RAG.
* **`staff`:** Perfil restringido. Únicamente puede interactuar con el endpoint de consultas `/rag/query` y recuperar metadatos básicos en modo lectura. Tiene vetada la subida de información y la visualización de la auditoría.

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

## 10. Roadmap Técnico del SPEC (Fases Futuras y Usabilidad)

### 10.1 Interfaz de Usuario de Alta Accesibilidad (Post-MVP)
* **Nexus CLI (Rich Interface):** Desarrollo de una interfaz de línea de comandos avanzada integrada en el ecosistema Python utilizando `Typer` y `Rich` para dotar al sistema de usabilidad para perfiles no técnicos.
  * Paneles visuales de colores y tablas estructuradas para mostrar metadatos.
  * Barras de progreso animadas en tiempo real durante los procesos de ingesta e inferencia de Ollama.
  * Menús interactivos en la terminal para seleccionar los documentos a incluir en el contexto.
* **Separación de Capas:** El backend mantendrá sus controladores desacoplados, garantizando que la CLI consuma los mismos servicios internos de la aplicación que la API, sin comprometer el diseño de monolito modular.

### 10.2 Hardening y Escalabilidad Corporativa
* Implementación de un sistema automatizado para la rotación de claves criptográficas y firmado de tokens.
* Incorporación de métricas avanzadas de rendimiento RAG (latencias de recuperación frente a tiempos de inferencia).
* Escalabilidad horizontal del motor de inferencia con soporte adaptativo para entornos híbridos CPU/GPU.
* Integración de la auditoría inmutable con sistemas SIEM corporativos mediante logs distribuidos con OpenTelemetry.