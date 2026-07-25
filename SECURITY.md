# SECURITY.md — Invariantes de Seguridad y Validación Zero-Trust

## 1. Propósito del documento
`Checkmate` define las reglas de seguridad, validación y comportamiento de cumplimiento obligatorio en Nexus Insight. Su objetivo es garantizar:
* Soberanía de datos y aislamiento hermético de servicios.
* Integridad documental mediante firmas criptográficas.
* Auditoría forense inmutable.
* Cumplimiento estricto del paradigma Zero-Trust.

Este documento complementa a `SPEC.md` y sirve como guía de control supremo para desarrolladores y agentes de IA.

---

## 2. Invariantes de Seguridad (Obligatorias - MVP 1.0)

### 2.1 Contenedores sin Privilegios (No-Root)
* **Regla:** Ningún servicio (`fastapi_app`, `db_service`, `ollama_service`) puede ejecutarse como usuario `root`.
* **Implementación:** Declarar explícitamente usuarios no privilegiados (`USER`) en los `Dockerfile` y en la configuración de Docker Compose.

### 2.2 Validación Criptográfica SHA-256 Previa
* **Regla:** Todo archivo recibido debe calcular su hash SHA-256 en memoria antes de cualquier tipo de persistencia.
* **Implementación:** Si el hash no se puede computar, la ingesta se rechaza de inmediato. No se almacena el documento físico.

### 2.3 Auditoría Inmutable (Append-Only)
* **Regla:** La tabla `AuditLog` solo permite la sentencia `INSERT`.
* **Implementación:** Configurar triggers físicos en PostgreSQL que bloqueen y lancen una excepción ante cualquier sentencia `UPDATE` o `DELETE`. Se auditan de forma obligatoria inicios de sesión, ingestas, consultas RAG y errores del sistema.

### 2.4 Aislamiento del Motor de IA (Ollama)
* **Regla:** El contenedor de IA opera aislado en la red interna `nexus-network` sin exponer puertos en producción.
* **Implementación:** Solo el backend FastAPI tiene permitido comunicarse con Ollama. La IA no tiene acceso a la base de datos ni a rutas físicas del sistema de archivos.

### 2.5 Aislamiento de la Base de Datos
* **Regla:** PostgreSQL es accesible únicamente por el backend FastAPI dentro de `nexus-network`.
* **Implementación:** Sin puertos expuestos al host exterior en producción. Los volúmenes persistentes deben estar protegidos.
* **SQL Injection:** Toda query se ejecuta mediante SQLAlchemy 2.0 con bind parameters. Queda prohibida la concatenación de strings de entrada de usuario en sentencias SQL.
* **Rollback automático:** El `get_session()` de `database.py` envuelve cada transacción en try/except → `session.rollback()` ante cualquier excepción, garantizando que no queden transacciones huérfanas.
* **Aislamiento dev/prod:** Los volúmenes de datos son independientes (`nexus_db_dev_data` vs `nexus_postgres_data_prod`). Nunca se mezclan datos de desarrollo con producción.

### 2.6 Prohibición de Secrets en Código (Hardcoding)
* **Regla:** Prohibido escribir tokens, contraseñas o firmas JWT en texto plano en el repositorio.
* **Implementación dev:** Variables de entorno inyectadas desde `.env` no versionado. `.env.example` contiene solo valores ficticios.
* **Implementación prod (OWASP):** Docker Secrets monta `admin_password.txt` como archivo en `/run/secrets/admin_password` dentro del contenedor. No visible en `docker inspect`, logs, ni `ps aux`. El seed lo lee mediante `ADMIN_PASSWORD_FILE`.
* **Hashing:** Contraseñas hasheadas con `argon2-cffi` (Argon2id). Sin almacenamiento en texto plano.
* **Admin username:** Configurable vía variable de entorno `NEXUS_ADMIN_USERNAME` (dev default: `"admin"`). No hardcodeado en el código de seed. Validación: si está vacío, el seed se aborta con error.
* **Namespace `NEXUS_`:** Todas las variables de entorno del proyecto usan el prefijo `NEXUS_` para evitar colisiones con variables del sistema o de otras aplicaciones (ej: `NEXUS_ENV`, `NEXUS_DATABASE_URL`).

### 2.7 Control de Acceso Basado en Roles (RBAC)
* **Regla:** Todos los endpoints sensibles (excepto login y health check) requieren validación JWT y rol verificado.
* **Implementación:** Jerarquía de tres niveles via `require_min_level(n)`:
  * `admin` (nivel 3): Acceso completo (Ingesta, AuditLog, consultas RAG).
  * `lead` (nivel 2): Acceso a endpoints de nivel 2 y 1.
  * `staff` (nivel 1): Subida de documentos, consultas RAG, lectura limitada.
* **Departamentos:** El JWT contiene `accessible_departments: list[int]`. Todos los endpoints de documentos filtran por esta lista (Zero-Trust). El usuario solo accede a documentos cuyo `department_id` esté en su lista.
* **Dependencias FastAPI:**
  * `get_current_user` extrae el token del header `Authorization: Bearer` vía `HTTPBearer(auto_error=False)`, lo verifica con `verify_token()`, y retorna los claims.
  * `get_current_user_from_cookie` extrae el token de la cookie `access_token` para autenticación via frontend (Jinja2/htmx).
  * `require_min_level(n)` es una factory que compara `ROLE_LEVELS[role] >= n`; si no → `403 Forbidden`.
  * `require_role(role)` se mantiene para compatibilidad (check exacto).

### 2.8 JWT (JSON Web Token)
* **Algoritmo:** HS256 (HMAC-SHA256) con `algorithms=["HS256"]` explícito en `jwt.decode()` para prevenir el ataque de confusión de algoritmos (CVE-2015-9235).
* **Claims estándar:** `iat` (emisión), `nbf` (no válido antes de), `exp` (expiración — por defecto 30 minutos, configurable vía `JWT_EXPIRATION_MINUTES`).
* **Claims personalizados:** `sub` (username), `role`, `department_id`, `accessible_departments` (list[int]), `user_id` (int). El token es la fuente de verdad zero-trust para el control de acceso departamental.
* **Secreto:** Inyectado desde variable de entorno `JWT_SECRET` (dev: `.env`, prod: `PROD_JWT_SECRET`). Nunca hardcodeado.
* **Anti-enumeration:** El servicio de autenticación (`authenticate_user`) devuelve el mismo resultado (`None`) tanto para usuario inexistente como para contraseña incorrecta, impidiendo la enumeración de usuarios por respuesta diferenciada.

### 2.9 Red Interna Zero-Trust
* **Regla:** Comunicación exclusiva entre contenedores mediante la red virtual de Docker `nexus-network`.
* **Implementación:** Ningún contenedor puede comunicarse de forma directa con el exterior o con otros servicios fuera de la red declarada.

### 2.10 Filosofía de Fallo Seguro (Fail-Closed)
* **Regla:** Ante cualquier caída o excepción no controlada en el subsistema de auditoría (`AuditLog`), el flujo operativo del backend debe interrumpirse inmediatamente.
* **Implementación:** Si un registro de auditoría síncrono falla al guardarse en PostgreSQL ➔ la transacción principal (ej. login o ingesta) se aborta con un rollback y se deniega el acceso al usuario.

### 2.11 Rate Limiting en Autenticación
* **Regla:** El endpoint `POST /api/v1/auth/login` tiene un límite de 5 peticiones por minuto por dirección IP.
* **Implementación:** Middleware `RateLimitMiddleware` con ventana deslizante in-memory (`collections.defaultdict` + timestamps). Tras el límite, devuelve `429 Too Many Requests` con JSON `{"detail": "Too many requests. Please try again later."}`.
* **Test:** 1 test que verifica 5 éxitos + 1 rechazo (TDD RED → GREEN).

### 2.12 Seguridad en Headers HTTP (CSP + Otros)
* **Regla:** Toda respuesta HTTP del backend debe incluir los siguientes headers de seguridad:
  * `Content-Security-Policy`: `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; form-action 'self'`
  * `X-Content-Type-Options: nosniff`
  * `X-Frame-Options: DENY`
  * `Referrer-Policy: strict-origin-when-cross-origin`
* **Implementación:** `SecurityHeadersMiddleware` (Starlette `BaseHTTPMiddleware`) añade los headers tras cada respuesta.
* **Test:** 1 test que verifica la presencia de los 4 headers en cualquier ruta.

### 2.13 Política de Complejidad de Contraseñas
* **Regla:** Toda contraseña debe cumplir:
  * Mínimo 8 caracteres
  * Al menos 1 letra mayúscula (`[A-Z]`)
  * Al menos 1 letra minúscula (`[a-z]`)
  * Al menos 1 dígito (`\d`)
  * Al menos 1 carácter especial (`[^A-Za-z0-9]`)
* **Implementación:** `validate_password_complexity()` en `security.py`. Se llama desde `create_user()` y `reset_password()` en `user_service.py`. Ante incumplimiento, lanza `ValueError` que el API captura y devuelve como `409 Conflict`.
* **Tests:** 6 tests unitarios (cada regla) + 4 tests de integración (service con SQLite in-memory).

### 2.14 Sanitización XSS en Salida RAG (DOMPurify)
* **Regla:** Todo contenido renderizado mediante `marked.parse()` debe ser sanitizado antes de inyectarse al DOM.
* **Implementación:** `DOMPurify.sanitize()` envuelve la salida de `marked.parse()` en el evento `htmx:afterSwap`. El script se carga desde `cdn.jsdelivr.net` (mismo origen CSP que marked). Adicionalmente, todos los enlaces generados por marked reciben `rel="noopener noreferrer"`.
* **CDN:** `https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js`
* **Test:** Cobertura manual (el sanitizador se ejecuta en cliente).

### 2.15 Validación de Tipo MIME en Subida Web
* **Regla:** El endpoint `POST /web/upload` debe verificar los magic bytes `%PDF` (0x25 0x50 0x44 0x46) antes de procesar el archivo, idéntico al endpoint API.
* **Implementación:** `content.startswith(b"%PDF")` tras leer el archivo. Si falla, devuelve error con `_upload_form.html`.
* **Test:** Cobertura manual (misma lógica que API, testeada en H4).

### 2.16 Sanitización de Memoria Transitoria
* **Regla:** El contenido de los documentos procesados en memoria RAM no debe persistir en el ciclo de vida del backend más allá de lo estrictamente necesario para el parsing.
* **Implementación:** Forzar la liberación o sobreescritura de buffers en memoria una vez que el texto ha sido extraído y enviado al flujo de inferencia.

### 2.17 Sanitización de Errores en Respuestas (OWASP A05:2021)
* **Regla:** Los mensajes de error expuestos al usuario no deben contener detalles internos del sistema (URLs, cadenas de conexión, stack traces, nombres de servicios). El error real debe registrarse en logs.
* **Implementación:**
  * **Health check:** `str(e)` en `health_service.py` se reemplaza por mensajes genéricos (`"Database connection failed"`, `"Ollama service unreachable"`). El error real se loggea con `logger.exception`.
  * **RAG query:** `str(exc)` en `web.py` se reemplaza por `"Error al procesar la consulta."`. El error real se loggea con `logger.warning`.
  * **API JSON:** Los errores en endpoints `/api/v1/*` devuelven `JSONResponse` con cuerpo `{"detail": "<mensaje>"}` y `Content-Type: application/json`, sin exponer trazas internas.
* **Test:** Verificación manual de que los errores no exponen información interna del sistema.

---

## 3. Observabilidad (Logs Estructurados)

Toda petición al backend genera un log JSON en stdout con el siguiente formato:

```json
{"time": "2026-07-16T20:00:00", "level": "INFO", "message": "Login successful", "user": "tfm_admin", "ip": "172.17.0.1"}
```

* **Campos obligatorios:** `time`, `level`, `message`.
* **Campos contextuales:** `user`, `ip`, `action`, `latency_ms`, `status_code`.
* **Niveles:** `INFO` (éxito), `WARNING` (intento fallido), `ERROR` (excepción).
* **Eventos de autenticación:** Se registran tanto intentos exitosos (`INFO`) como fallidos (`WARNING`) de login. El mensaje nunca incluye la contraseña ni el token JWT.
* **Destino:** stdout del contenedor (`docker compose logs -f fastapi_app`).
* **No se almacenan** prompts de usuario ni contenido de documentos en los logs.

---

## 4. Validaciones Automáticas (Checklist de Control)

El sistema (y los agentes de IA) deben verificar automáticamente los siguientes puntos antes de dar una tarea por completada:

### 4.1 Infraestructura y Contenedores
* [ ] Todos los `Dockerfile` declaran un usuario no root.
* [ ] El archivo `docker-compose.prod.yml` no expone puertos de PostgreSQL (5432) ni de Ollama (11434).
* [ ] Los volúmenes locales de persistencia están declarados correctamente.

### 4.2 Lógica de Seguridad y Base de Datos
* [ ] La subida de documentos calcula el SHA-256 en memoria y verifica duplicados.
* [ ] El trigger anti-modificación/borrado de `AuditLog` está activo en la base de datos.
* [ ] El archivo `.env.example` no contiene credenciales reales ni claves secretas de producción.

### 4.3 Comportamiento del Backend
* [ ] Todos los endpoints implementan inyección de dependencias para validación de JWT y roles.
* [ ] Las respuestas de inferencia RAG generan de forma síncrona un registro en `AuditLog`.
* [ ] Los logs del sistema se emiten de forma estructurada en formato JSON en consola.
* [ ] El endpoint `/api/v1/auth/login` tiene rate limiting activo (5/min).
* [ ] Todas las respuestas HTTP incluyen headers de seguridad (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`).
* [ ] La creación y reseteo de contraseñas validan complejidad OWASP.
* [ ] La directiva `_NO_INVENT` del prompt RAG está activa y adaptada al modelo 1.5B.
* [ ] El contenido de `marked.parse()` se sanitiza con DOMPurify antes de inyectarse al DOM.
* [ ] La subida web de documentos valida magic bytes `%PDF`.
* [ ] Los enlaces generados por marked incluyen `rel="noopener noreferrer"`.
* [ ] La contraseña no se reenvía en `form_data` del formulario de creación de usuario (OWASP).
* [ ] El formulario de creación de usuario incluye confirmación de contraseña y validación en tiempo real.
* [ ] Los errores RAG no exponen detalles internos al usuario; se devuelve mensaje genérico y se loguea el error real.
* [ ] Los errores de health check no exponen URLs internas ni cadenas de conexión; se devuelve mensaje genérico y se loguea el error real.

---

## 5. Casos Límite y Manejo de Errores

| Evento o Condición Anómala | Acción del Backend | Código de Estado HTTP | Registro en Auditoría |
| :--- | :--- | :--- | :--- |
| Archivo corrupto o ilegible | Abortar procesamiento | `400 Bad Request` | No registra |
| Hash SHA-256 ya existente | Rechazar duplicado | `400 Bad Request` | Registra intento |
| Token JWT ausente o expirado | Bloquear petición | `401 Unauthorized` | Registra fallo |
| Credenciales inválidas (login) | Rechazar autenticación | `401 Unauthorized` | JSON log (AuditLog en H6) |
| Usuario `staff` intenta subir documento | Bloquear acceso | `403 Forbidden` | Registra violación |
| Identificador de documento inexistente | Retornar vacío | `404 Not Found` | No registra |
| Fallo al escribir en `AuditLog` | Abortar transacción principal (Rollback) | `500 Internal Error` | Registro en consola JSON (Contingencia) |
| Caída de base de datos o de Ollama | Activar logs de contingencia | `500 Internal Error` | Registra en consola |

---

## 6. Matriz de Trazabilidad Obligatoria
Cada invariante de seguridad declarada en la sección 2 debe estar respaldada de forma obligatoria por:
1. **Un Test:** Prueba unitaria o de integración en Pytest que intente violar deliberadamente la regla (ej: inyectar un payload sin JWT y validar el rechazo).
2. **Un Endpoint:** Vinculación directa con los contratos definidos en `SPEC.md`.
3. **Un Log:** Registro inmutable del evento correspondiente dentro del `AuditLog`.

---

## 7. Roadmap de Seguridad e Interfaces (Futuro / Post-MVP)

Para asegurar la escalabilidad del sistema, las decisiones de diseño del MVP deben dejar preparado el terreno para:
* **CLI Interactivo (Nexus CLI):** Mantener la lógica de consultas RAG desacoplada de FastAPI en `src/core/` para que la futura interfaz de terminal (`Typer`/`Rich`) consuma las funciones sin duplicar código.
* **Validación Automática de Prompts:** Capas de filtrado de entrada para prevenir inyecciones indirectas en prompts antes de enviarlos a Ollama.
* **Hardening de Persistencia Volátil (RAM):** Migración de los directorios de procesamiento temporal y cachés de contexto de Ollama hacia volúmenes en memoria RAM virtualizada (`tmpfs`), garantizando que la pérdida de corriente elimine cualquier dato residual.
* **Rotación Criptográfica:** Modularidad en el servicio de tokens para cambiar de algoritmos de firma de manera ágil.
* **Observabilidad Avanzada (OpenTelemetry):** Inclusión de un identificador de petición (`request_id`) en los logs del MVP para facilitar la futura transición a trazabilidad distribuida y sistemas SIEM.
* **Alta Disponibilidad (HA):** Diseño del backend sin estado (*stateless*) para permitir balanceo de carga en futuras fases corporativas.

---

## 8. Estado del Documento
* **Versión:** MVP 1.0  
* **Última actualización:** 25 de Julio de 2026  
* **Responsable:** Arquitectura de Seguridad Nexus Insight  
* **Cambios:** Añadidas invariantes 2.6 (namespace NEXUS_), 2.11 (rate limiting), 2.12 (CSP), 2.13 (password complexity), 2.14 (DOMPurify XSS), 2.15 (MIME subida web), 2.17 (sanitización errores OWASP). Renumeradas 2.11→2.16, 2.14→2.16. Añadido `'unsafe-eval'` a CSP por HTMX hx-on. Añadidos checklist OWASP (password en form_data, confirmación pw, validación tiempo real, errores RAG genéricos, errores health genéricos).

---
**All Rights Reserved.** Copyright © 2026 Khora Nexus Insight. Este documento es parte de un TFM y no puede ser reproducido sin autorización.