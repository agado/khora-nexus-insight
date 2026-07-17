#!/usr/bin/env python3
"""Khora Nexus Insight CLI — Wrapper para tareas habituales del proyecto."""

import argparse
import os
import subprocess
import sys
import webbrowser
from typing import TextIO

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[assignment]

VERSION = "0.1.0"

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
        print("Docker no está disponible. Asegúrate de que Docker Desktop esté en ejecución.")
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


if __name__ == "__main__":
    main()
