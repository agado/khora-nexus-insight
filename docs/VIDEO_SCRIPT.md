# Video Demo — Nexus Insight

**Duración estimada:** 5-7 minutos

---

## Escena 1: Introducción (0:00 – 0:45)

**Narración:**
> "Hola, soy [tu nombre] y os presento Nexus Insight, mi Trabajo de Fin de Máster.
> Nexus Insight es una plataforma de análisis documental inteligente diseñada bajo un paradigma Zero-Trust.
> ¿El problema? Las empresas no pueden usar ChatGPT con datos sensibles por riesgo de fuga,
> los costes de API son impredecibles, y la comunicación entre departamentos pierde contexto.
> Nexus Insight soluciona esto con IA 100% local, aislamiento departamental estricto,
> y adaptación automática del lenguaje según el rol del usuario."

**Pantalla:** Presentación de diapositivas abierta en la slide 1 (título) o 2 (problema).

---

## Escena 2: Arquitectura (0:45 – 1:30)

**Narración:**
> "La arquitectura es un monolito modular en Docker. FastAPI actúa como único punto de entrada.
> PostgreSQL y Ollama están aislados en una red interna sin puertos expuestos al host.
> El modelo Qwen2.5-Coder se ejecuta íntegramente en local: cero costes, cero fugas de datos.
> Todo el código sigue Clean Architecture con separación clara entre controladores, servicios e infraestructura."

**Pantalla:** Slide 4 (arquitectura) o abrir `docs/slides.html` en la sección de arquitectura.
Breve pausa para señalar los componentes en el diagrama.

---

## Escena 3: Demo — Login (1:30 – 2:15)

**Narración:**
> "Vamos a verlo en funcionamiento. Abro la aplicación en el navegador.
> Me logueo como admin. Observad que la cookie es httpOnly con SameSite=Lax.
> Si intento login con credenciales incorrectas, el mensaje es genérico — no revela si el usuario existe,
> evitando enumeración. Y si fallo 5 veces en un minuto, el rate limiter me bloquea con un 429."

**Pantalla:**
1. `start http://localhost:8000` en terminal
2. Login con `admin` / `admin123` → dashboard
3. Cerrar sesión, login incorrecto → mensaje genérico
4. (Opcional) mostrar 429 con curl o a velocidad rápida

---

## Escena 4: Demo — Subida de documento (2:15 – 3:00)

**Narración:**
> "Como admin, accedo a la pestaña de subida. Selecciono un PDF.
> El sistema calcula el SHA-256 en memoria antes de almacenarlo, detecta duplicados,
> y extrae el texto mediante PyPDF. Si intento subir un archivo que no sea PDF,
> lo rechaza en el servidor verificando los magic bytes."

**Pantalla:**
1. Ir a Documentos → Upload
2. Subir un PDF real
3. Mostrar mensaje de éxito con SHA-256
4. Intentar subir un .txt → error "Formato inválido"

---

## Escena 5: Demo — Consulta RAG con adaptación de tono (3:00 – 4:30)

**Narración:**
> "Ahora la funcionalidad clave: la consulta RAG con adaptación de tono.
> Selecciono documentos, escribo una pregunta, y elijo la audiencia.
> Por ejemplo: '¿Cuáles son los requisitos del sistema?' en modo Técnico vs Ejecutivo.
> La respuesta en modo técnico incluirá detalles de implementación.
> En modo ejecutivo se centrará en plazos, recursos e impacto de negocio.
> El spinner aparece durante la consulta, y al recibir la respuesta,
> se renderiza en Markdown sanitizado con DOMPurify. Todas las citas son clicables."

**Pantalla:**
1. Ir a Consultar
2. Seleccionar documentos
3. Escribir pregunta, elegir "Técnico" → respuesta detallada
4. Nueva consulta con "Ejecutivo" → respuesta resumida orientada a negocio
5. Señalar el spinner, el markdown renderizado, y las fuentes citadas

---

## Escena 6: Demo — Administración y Auditoría (4:30 – 5:15)

**Narración:**
> "Como admin, puedo gestionar usuarios: crear, editar rol y departamentos, resetear contraseña.
> Cada acción queda registrada en el log de auditoría inmutable.
> La tabla audit_log tiene un trigger a nivel de base de datos que rechaza任何 UPDATE o DELETE.
> Esto garantiza trazabilidad forense completa."

**Pantalla:**
1. Ir a Usuarios
2. Crear nuevo usuario, asignar rol staff, departamento IT
3. Mostrar el log en la pestaña Registros
4. (Opcional) Mostrar el trigger SQL en consola

---

## Escena 7: Cierre (5:15 – 6:00)

**Narración:**
> "Nexus Insight completa 9 hitos con 251 tests automatizados, cero dependencias cloud,
> y seguridad en profundidad verificada por tests que intentan violar cada invariante.
> Es desplegable con un solo comando: docker compose up --build.
> El código está disponible en github.com/agado/khora-nexus-insight.
> Muchas gracias. ¿Preguntas?"

**Pantalla:** Slide 9 (gracias) o el repo de GitHub abierto en el navegador.

---

## Notas técnicas para la grabación

- **Resolución:** 1920×1080 mínimo
- **Ventana:** Navegador en pantalla completa, terminal a la derecha si es necesario
- **Audio:** Micrófono claro, sin ruido de fondo
- **Herramientas sugeridas:** OBS Studio (gratuito) para captura + edición
- **Ritmo:** Pausa de 1-2 segundos entre escenas. No apresurarse.
- **Slides:** Tener `docs/slides.html` abierto en una pestaña para las escenas 1-2 y 7

## Enlaces

- Repositorio: `https://github.com/agado/khora-nexus-insight`
- Slides (HTML): `docs/slides.html` (abrir en navegador, navegar con teclas ← →)
