# Nexus Insight

## a. Descripción general del proyecto

<details> <summary>Descripción para técnicos (por defecto)</summary>

Nexus Insight es una plataforma de análisis documental inteligente diseñada bajo el paradigma Zero ‑Trust y una arquitectura monolito modular. Su objetivo es permitir la ingesta, procesamiento e inferencias RAG 100% locales, garantizando que la información confidencial nunca abandone la infraestructura física del cliente.

La IA se ejecuta en un contenedor aislado dentro de una red interna de Docker, cumpliendo los requisitos de soberanía de datos y seguridad corporativa.

Puntos clave para técnicos:

Seguridad y soberanía: Arquitectura y ejecución local para máxima privacidad.

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
* Automatización: Makefile (MVP).
* Calidad de código: Ruff + pre‑commit.
* Pruebas: Pytest + pytest-asyncio con mocking.

## c. Información sobre su instalación y ejecución

0. Clonar el repositorio
``` bash
git clone https://github.com/tu-org/nexus-insight.git
cd nexus-insight
```
1. Preparar entorno
``` bash
cp .env.example .env
```
2. Desplegar infraestructura (vía Makefile)
``` bash
make dev
```
3. Apagar infraestructura
``` bash
make down
```
4. Inicializar el modelo de IA (solo primera vez)
``` bash
docker compose exec ollama_service ollama run qwen2.5:1.5b
```
5. Acceso a la API

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
├── requirements.txt
├── agents.md
├── ruff.toml
├── SPEC.md
└── src/
    ├── main.py
    ├── checkmate.md
    ├── api/
    │   └── v1/
    │       ├── auth.py
    │       └── documents.py
    ├── core/
    │   ├── config.py
    │   ├── database.py
    │   ├── auth/
    │   │   ├── rbac.py
    │   │   └── security.py
    │   └── storage/
    └── tests/
        ├── conftest.py
        └── test_auth.py


## e. Funcionalidades principales

* Ingesta con validación criptográfica:Cálculo de SHA‑256 en memoria antes de almacenar metadatos.

* Flujo RAG 100% local:Recuperación contextual por rol + generación en contenedor aislado de Ollama.

* Auditoría inmutable (Zero‑Trust):Tabla append‑only con triggers que bloquean UPDATE/DELETE.

* RBAC:Roles administrados por entorno (tfm_admin, tfm_staff).

* Observabilidad nativa:Logs JSON estructurados sin latencia de red.

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

* Credenciales de desarrollo incluidas en .env.example:

 * Administrador:
 Usuario: tfm_admin
 Contraseña: admin123

 * Staff:
 Usuario: tfm_staff
 Contraseña: staff123

(Nunca usar estas credenciales en producción.)



## g. Estado actual y RoadMap (Desarrollo Guiado por TDD)

Fase,Entregable,Funcionalidad Clave,Testeable (Definition of Done)
Fase 1,Scaffolding,"Estructura, orquestación Docker y FastAPI base",GET /health responde HTTP 200
Fase 2,Capa de Datos,PostgreSQL + Modelos SQLAlchemy asíncronos,Conexión DB y creación de tablas automática
Fase 3,Seguridad,Auth (JWT/RBAC) + Validación Pydantic estricta,Tests de Login OK + Bloqueo de rutas protegidas
Fase 4,Motor de IA,Integración con servicio Ollama (vía API),Respuesta del flujo RAG (mockeada en tests)
Fase 5,Integridad,Sistema de auditoría y almacenamiento local blindado,Registros verificables en tabla AuditLog

### Mapa MVP (implementado)

* Arquitectura monolito modular.
* Contenedor aislado para IA.
* PostgreSQL + SQLAlchemy async.
* RBAC + JWT + Argon2id.
* Auditoría append‑only.
* Ingesta con SHA‑256.
* Pruebas con Pytest.
* Ruff + pre‑commit.
* Docker Compose.
* Makefile básico (dev/down).
* Documentación Swagger.

### Roadmap futuro (no implementado aún)

* Rotación de claves criptográficas.
* Métricas avanzadas de rendimiento RAG.
* Modelos IA escalables por CPU/GPU.
* Sharding de documentos y colas de procesamiento.
* Integración con SIEM corporativos.
* Hardening avanzado de contenedores.
* Observabilidad con OpenTelemetry.
* Makefile ampliado (deploy, coverage, linting avanzado).
* Modo HA en producción.


## Metodología TDD

A partir de la estructura, aplicamos TDD en toda la lógica de negocio:

1. RED:    Escribir test PRIMERO → ejecutar → DEBE FALLAR
2. GREEN:  Implementar código MÍNIMO para pasar el test
3. REFACTOR: Mejorar el código manteniendo tests verdes

## Mejora Pareto para Observabilidad y Testing

Para maximizar el impacto con el menor esfuerzo en esta fase MVP, se recomienda priorizar:

Automatización de tests críticos: Garantizar que los endpoints y funcionalidades clave (como /health, autenticación y flujo RAG) tengan tests automatizados robustos y confiables.

Monitoreo básico de logs estructurados: Asegurar que los logs JSON generados incluyan trazas de errores, tiempos de respuesta y eventos clave para facilitar la detección rápida de fallos.

Integración continua con validación automática: Configurar pipelines que ejecuten tests, linting y type checking en cada commit para evitar regresiones tempranas.

Feedback rápido: Mantener tiempos cortos de ejecución de tests para que el equipo reciba retroalimentación inmediata y pueda corregir rápido.

Documentación clara y accesible: Mantener actualizadas las secciones de testing y observabilidad para que cualquier miembro del equipo pueda entender y contribuir fácilmente.

Estas acciones representan un enfoque Pareto que asegura calidad y visibilidad sin sobrecargar recursos en esta etapa inicial.

## Estrategia de Desarrollo Incremental Recomendada

Para asegurar un desarrollo seguro, trazable y de alta calidad, se recomienda seguir esta estrategia incremental:

Avanzar por casos pequeños y funcionales, comenzando por un endpoint básico como /health.

Validar y probar cada funcionalidad incremental antes de continuar con la siguiente.

Realizar un commit en Git solo cuando la funcionalidad mínima implementada pase todos los tests automatizados asociados y esté lista para integrarse.

Mantener una disciplina estricta de versionado en Git: commits frecuentes, descriptivos y que representen cambios funcionales estables.

Esta práctica debe ser seguida tanto por desarrolladores humanos como por agentes de IA que contribuyan al código, actuando como una segunda vigilancia para asegurar calidad y alineación con buenas prácticas de SDD, TDD y SSDLC.

Esta estrategia fomenta un desarrollo controlado, con alta calidad y alineado con los principios de Spec Driven Development y Test Driven Development.

---

## Métricas Objetivo

Al finalizar las fases tendrás:

- ~100 tests unitarios/integración
- ~7 tests E2E
- 80%+ cobertura de código
- 0 errores de lint

---

## Prácticas aplicadas

- TDD (Test-Driven Development)
- Testing (Unit, Integration, E2E)
- Clean Code (Refactoring, code smells)
- Design Patterns (Strategy Pattern)
- Security (Password validation)
- Accessibility (WCAG AA)
- UX ( clean minimal interface,)
- Observability (logs,)
- Quality Gates ( hooks)
---

## Checklist Final

Antes de considerar el proyecto completo, verifica:

✅ make dev         → App funciona en desarrollo
✅ make lint        → 0 errores
✅ make typecheck   → 0 errores
✅ make test:run    → Todos los tests pasan
✅ make test:e2e    → E2E tests pasan
✅ make build       → Build exitoso
✅ make preview     → App funciona en producción

✅ Pre-commit hook  → Bloquea commits con errores
✅ Pre-push hook    → Bloquea push si tests fallan

✅ Accesibilidad    → Score 90+ en Lighthouse
✅ Coverage         → 80%+ en todas las métricas