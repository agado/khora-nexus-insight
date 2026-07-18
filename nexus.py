#!/usr/bin/env python3
"""Khora Nexus Insight CLI — Wrapper para tareas habituales del proyecto."""

import argparse
import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import TextIO

import requests
from requests.exceptions import ConnectionError as ReqConnectionError

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[assignment]

VERSION = "0.3.0"

BANNER = f"""
 +------------------------------------------+
 |         Khora Nexus Insight              |
 |   Zero-Trust RAG Platform - v{VERSION}   |
 |   Secure . Local . Modular               |
 |   Donde los datos encuentran su alma     |
 +------------------------------------------+
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        add_help=False,
        description="Khora Nexus Insight - Zero-Trust RAG Platform CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-h", "--help", action="store_true", help="Muestra esta ayuda")
    sub = parser.add_subparsers(dest="command", title="commands", metavar="")
    sub.add_parser("dev", help="Inicia el entorno de desarrollo (docker compose up --build)")
    sub.add_parser("down", help="Detiene el entorno de desarrollo")
    sub.add_parser("prod", help="Inicia el entorno de produccion")
    sub.add_parser("test", help="Ejecuta los tests (pytest -v)")
    sub.add_parser("cov", help="Ejecuta tests con cobertura")
    seed_parser = sub.add_parser("seed", help="Puebla la base de datos con datos iniciales")
    seed_parser.add_argument(
        "--reset", action="store_true", help="Elimina los datos existentes antes de insertar"
    )
    sub.add_parser("migrate", help="Ejecuta migraciones de base de datos")
    upload_parser = sub.add_parser("upload", help="Sube un documento a la API via HTTP")
    upload_parser.add_argument("filepath", help="Ruta al archivo PDF")
    upload_parser.add_argument("--department-id", type=int, help="Depto ID (default: del JWT)")
    upload_parser.add_argument("--token", required=True, help="Token JWT de acceso")
    doc_parser = sub.add_parser("document", help="Operaciones sobre documentos")
    doc_sub = doc_parser.add_subparsers(dest="document_command")
    get_parser = doc_sub.add_parser("get", help="Obtiene un documento por ID")
    get_parser.add_argument("id", type=int, help="ID del documento")
    get_parser.add_argument("--token", required=True, help="Token JWT de acceso")
    list_parser = doc_sub.add_parser("list", help="Lista documentos accesibles")
    list_parser.add_argument("--token", required=True, help="Token JWT de acceso")
    list_parser.add_argument("--skip", type=int, default=0, help="Numero de documentos a saltar")
    list_parser.add_argument("--limit", type=int, default=50, help="Maximo de documentos a mostrar")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = _build_parser()
    return parser.parse_args(argv)


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def print_banner(output_file: TextIO | None = None, clear: bool = True) -> None:
    output_file = output_file or sys.stdout
    if clear:
        clear_screen()
    print(BANNER, file=output_file)


def preflight_docker() -> None:
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print(
            "Docker no está disponible. Asegúrate de que Docker Desktop"
            " esté en ejecución. (docker desktop start)"
        )
        sys.exit(1)


def preflight_pytest() -> None:
    try:
        subprocess.run(["pytest", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("pytest no está instalado. Ejecuta: pip install -r requirements.txt")
        sys.exit(1)
    try:
        subprocess.run([sys.executable, "-c", "import pytest_cov"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("pytest-cov no está instalado. Ejecuta: pip install -r requirements.txt")
        sys.exit(1)


def run_dev() -> None:
    preflight_docker()
    clear_screen()
    print_banner()
    print("Iniciando Khora Nexus...\n")
    try:
        result = subprocess.run(["docker", "compose", "up", "--build"])
        if result.returncode == 0:
            webbrowser.open("http://localhost:8000/docs")
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nEntorno detenido.")
        sys.exit(0)


def run_down() -> None:
    preflight_docker()
    print("Deteniendo entorno...")
    try:
        subprocess.run(["docker", "compose", "down"])
        subprocess.run(["docker", "compose", "-f", "docker-compose.prod.yml", "down"])
    except KeyboardInterrupt:
        print("\nOperacion cancelada.")
        sys.exit(0)


def run_prod() -> None:
    preflight_docker()
    if load_dotenv is not None:
        load_dotenv()
    required_prod_vars = (
        "PROD_DB_USER",
        "PROD_DB_PASSWORD",
        "PROD_DB_NAME",
        "PROD_JWT_SECRET",
        "PROD_MODEL_NAME",
    )
    missing = [v for v in required_prod_vars if not os.environ.get(v)]
    if missing:
        print("ERROR: No se puede iniciar entorno de producción.", flush=True)
        print(f"Variables requeridas no definidas: {', '.join(missing)}", flush=True)
        print("Defínelas en .env o expórtalas en tu shell.", flush=True)
        sys.exit(1)
    print("Iniciando entorno de producción...", flush=True)
    try:
        subprocess.run(["docker", "compose", "-f", "docker-compose.prod.yml", "up", "--build"])
    except KeyboardInterrupt:
        print("\nEntorno detenido.")
        sys.exit(0)


def run_test() -> None:
    preflight_pytest()
    clear_screen()
    print_banner()
    subprocess.run(["pytest", "-v"])


def run_cov() -> None:
    preflight_pytest()
    clear_screen()
    print_banner()
    subprocess.run(["pytest", "--cov=src", "--cov-report=term-missing"])


def run_seed(reset: bool = False) -> None:
    print("Poblando base de datos con datos iniciales...")
    cmd = [sys.executable, "-m", "src.core.seed"]
    if reset:
        cmd.append("--reset")
    subprocess.run(cmd)


def run_migrate() -> None:
    print("Ejecutando migraciones de base de datos...")
    subprocess.run(["alembic", "upgrade", "head"])


API_BASE = "http://localhost:8000/api/v1"


def _api_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _api_get(path: str, token: str, params: dict | None = None) -> requests.Response:
    try:
        response = requests.get(
            f"{API_BASE}{path}",
            headers=_api_headers(token),
            params=params,
        )
    except ReqConnectionError:
        print(
            "Error: no se pudo conectar con el servidor."
            " Asegurate de que 'nexus.py dev' este en ejecucion."
        )
        sys.exit(1)
    return response


def _api_post_file(
    path: str, token: str, files: dict, data: dict | None = None
) -> requests.Response:
    try:
        response = requests.post(
            f"{API_BASE}{path}",
            headers=_api_headers(token),
            files=files,
            data=data,
        )
    except ReqConnectionError:
        print(
            "Error: no se pudo conectar con el servidor."
            " Asegurate de que 'nexus.py dev' este en ejecucion."
        )
        sys.exit(1)
    return response


def _handle_http_error(response: requests.Response) -> None:
    try:
        detail = response.json().get("detail", response.reason)
    except (json.JSONDecodeError, AttributeError):
        detail = response.reason
    print(f"Error {response.status_code}: {detail}")
    sys.exit(1)


def run_upload(filepath: str, department_id: int | None, token: str) -> None:
    path = Path(filepath)
    if not path.is_file():
        print(f"Error: archivo no encontrado: {filepath}")
        sys.exit(1)

    with path.open("rb") as f:
        files = {"file": (path.name, f, "application/pdf")}
        data = {}
        if department_id is not None:
            data["department_id"] = str(department_id)
        response = _api_post_file("/documents/upload", token, files, data)

    if not response.ok:
        _handle_http_error(response)

    doc = response.json()
    print(f"Documento subido: id={doc['id']} filename={doc['filename']}")
    print(f"  SHA-256: {doc['sha256']}")
    print(f"  Departmento: {doc['department_id']}")
    print(f"  Creado: {doc['created_at']}")


def run_document_get(document_id: int, token: str) -> None:
    response = _api_get(f"/documents/{document_id}", token)

    if not response.ok:
        _handle_http_error(response)

    doc = response.json()
    print(f"Documento: id={doc['id']}")
    print(f"  Nombre: {doc['filename']}")
    print(f"  SHA-256: {doc['sha256']}")
    print(f"  Departmento: {doc['department_id']}")
    print(f"  Subido por: {doc['uploaded_by']}")
    print(f"  Creado: {doc['created_at']}")


def run_document_list(token: str, skip: int = 0, limit: int = 50) -> None:
    response = _api_get("/documents", token, params={"skip": skip, "limit": limit})

    if not response.ok:
        _handle_http_error(response)

    data = response.json()
    docs = data.get("documents", [])
    total = data.get("total", len(docs))

    if not docs:
        print("No hay documentos disponibles.")
        return

    print(f"Documentos ({total} en total):")
    for doc in docs:
        ts = doc["created_at"][:10]
        print(f"  [{doc['id']}] {doc['filename']} — Depto {doc['department_id']} — {ts}")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.help:
        print_banner(clear=False)
        _build_parser().print_help()
        return
    if not args.command:
        print_banner()
        _build_parser().print_help()
        return
    if args.command == "dev":
        run_dev()
    elif args.command == "down":
        run_down()
    elif args.command == "prod":
        run_prod()
    elif args.command == "test":
        run_test()
    elif args.command == "cov":
        run_cov()
    elif args.command == "seed":
        run_seed(reset=getattr(args, "reset", False))
    elif args.command == "migrate":
        run_migrate()
    elif args.command == "upload":
        run_upload(
            filepath=args.filepath,
            department_id=args.department_id,
            token=args.token,
        )
    elif args.command == "document":
        if not args.document_command:
            print(
                "Error: especifica un subcomando."
                " Uso: nexus.py document get <id> | nexus.py document list"
            )
            sys.exit(1)
        elif args.document_command == "get":
            run_document_get(document_id=args.id, token=args.token)
        elif args.document_command == "list":
            run_document_list(
                token=args.token,
                skip=getattr(args, "skip", 0),
                limit=getattr(args, "limit", 50),
            )


if __name__ == "__main__":
    main()
