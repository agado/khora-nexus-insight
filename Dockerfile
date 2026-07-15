# ==============================================================================
# ETAPA 1: Compilación de dependencias (Builder)
# ==============================================================================
FROM python:3.12.9-slim-bookworm AS builder

WORKDIR /app

# Evita que Python escriba archivos .pyc y fuerza el vaciado de buffers de logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instalar dependencias del sistema necesarias para compilar librerías de Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y generar los wheels (paquetes precompilados)
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ==============================================================================
# ETAPA 2: Entorno de ejecución ultra-seguro (Runner)
# ==============================================================================
FROM python:3.12.9-slim-bookworm AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Instalar solo las dependencias de ejecución de Postgres (libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario y grupo del sistema sin privilegios (Zero-Trust)
RUN groupadd -g 10001 nexus_group && \
    useradd -u 10001 -g nexus_group -s /sbin/nologin -m nexus_user

# Copiar las dependencias instaladas desde la etapa de compilación
COPY --from=builder --chown=nexus_user:nexus_group /root/.local /home/nexus_user/.local
COPY --chown=nexus_user:nexus_group . .

# Añadir el path de las librerías instaladas por el usuario al PATH del sistema
ENV PATH=/home/nexus_user/.local/bin:$PATH

# Cambiar al usuario no-root antes de iniciar la ejecución
USER nexus_user

EXPOSE 8000

# Arrancar la aplicación usando Uvicorn (FastAPI)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]