# ==============================================================================
# NEXUS INSIGHT — MAKEFILE DE AUTOMATIZACIÓN (MVP)
# ==============================================================================

# Variables de entorno y comandos Docker
ENV_FILE=.env
DC_DEV=docker compose -f $(COMPOSE_DEV) --env-file $(ENV_FILE)
DC_PROD=docker compose -f $(COMPOSE_PROD)

# Archivos de Compose
COMPOSE_DEV=docker-compose.yml
COMPOSE_PROD=docker-compose.prod.yml

# Extracción dinámica de variables de configuración de .env
MODEL_NAME := $(shell grep MODEL_NAME $(ENV_FILE) | cut -d '=' -f2 | xargs)
API_PORT   := $(shell grep API_PORT $(ENV_FILE) | cut -d '=' -f2 | xargs)
DB_PORT    := $(shell grep DB_PORT $(ENV_FILE) | cut -d '=' -f2 | xargs)

.PHONY: setup dev dev-no-ai down restart test lint format logs model start-ai stop-ai prod prod-down clean help

# ------------------------------------------------------------------------------
# Ayuda
# ------------------------------------------------------------------------------
help: ## Muestra los comandos disponibles
	@echo "Comandos disponibles para Nexus Insight:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ------------------------------------------------------------------------------
# Instalación e Inicialización Inteligente (Fácil UX)
# ------------------------------------------------------------------------------
setup: dev ## Levanta el entorno de desarrollo e inicializa/descarga el modelo de IA automáticamente
	@echo "Esperando a que el servicio de IA (Ollama) responda..."
	@until $(DC_DEV) exec ollama_service ollama list >/dev/null 2>&1; do \
		echo "Aún inicializando Ollama... reintentando en 2 segundos."; \
		sleep 2; \
	done
	@echo "Descargando e inicializando el modelo '$(MODEL_NAME)'..."
	$(DC_DEV) exec ollama_service ollama pull $(MODEL_NAME)
	@echo "🚀 ¡Todo configurado e inicializado! API corriendo en http://localhost:$(API_PORT)"

# ------------------------------------------------------------------------------
# Desarrollo
# ------------------------------------------------------------------------------
dev: ## Levanta el entorno de desarrollo local validando puertos disponibles
	@echo "Validando puertos libres en el host..."
	@if lsof -Pi :$(API_PORT) -sTCP:LISTEN -t >/dev/null ; then \
		echo "❌ Error: El puerto $(API_PORT) configurado para la API ya está en uso."; \
		exit 1; \
	fi
	@if lsof -Pi :$(DB_PORT) -sTCP:LISTEN -t >/dev/null ; then \
		echo "❌ Error: El puerto $(DB_PORT) configurado para Postgres ya está en uso."; \
		exit 1; \
	fi
	@echo "Puertos libres. Levantando contenedores..."
	$(DC_DEV) up --build -d

dev-no-ai: ## Levanta solo la API y la Base de Datos para desarrollo rápido sin IA
	$(DC_DEV) up --build -d fastapi_app db_service

down: ## Apaga y remueve los contenedores del entorno local
	$(DC_DEV) down

restart: ## Reinicia el entorno de desarrollo
	$(DC_DEV) down
	$(DC_DEV) up --build -d

# ------------------------------------------------------------------------------
# Backend
# ------------------------------------------------------------------------------
test: ## Ejecuta la suite de pruebas (Pytest) dentro del contenedor
	$(DC_DEV) exec fastapi_app pytest -v -s src/tests/

lint: ## Ejecuta el linter Ruff para comprobar la calidad del código
	$(DC_DEV) exec fastapi_app ruff check src/

format: ## Formatea el código automáticamente usando Ruff
	$(DC_DEV) exec fastapi_app ruff format src/

logs: ## Muestra logs del backend en tiempo real
	$(DC_DEV) logs -f fastapi_app

# ------------------------------------------------------------------------------
# IA Local (Ollama)
# ------------------------------------------------------------------------------
model: ## Inicializa el modelo de IA y lo descarga manualmente (definido en .env)
	$(DC_DEV) exec ollama_service ollama run $(MODEL_NAME)

start-ai: ## Enciende de forma independiente el motor de IA (Ollama)
	$(DC_DEV) start ollama_service

stop-ai: ## Apaga temporalmente el motor de IA para pruebas de resiliencia
	$(DC_DEV) stop ollama_service

# ------------------------------------------------------------------------------
# Producción
# ------------------------------------------------------------------------------
prod: ## Levanta el entorno de producción (Zero-Trust)
	$(DC_PROD) up --build -d

prod-down: ## Apaga el entorno de producción
	$(DC_PROD) down

# ------------------------------------------------------------------------------
# Limpieza
# ------------------------------------------------------------------------------
clean: ## Limpia cachés y archivos temporales de Python y de herramientas
	rm -rf .pytest_cache .ruff_cache src/**/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete