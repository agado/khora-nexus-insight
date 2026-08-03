from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ollama_healthcheck_expands_model_name():
    """Regresion (despliegue VPS real): las comillas simples dejaban el
    patron literal '${MODEL_NAME}' en el healthcheck, por lo que ollama
    nunca llegaba a 'healthy' y bloqueaba todo el stack."""
    compose = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "grep -q '$${MODEL_NAME}'" not in compose
    assert 'grep -q \\"$${MODEL_NAME}\\"' in compose


def test_setup_vps_secret_legible_por_contenedor():
    """Regresion (despliegue VPS real): chmod 600 hacia ilegible el secret
    admin para el usuario no-root del contenedor (PermissionError al seed)."""
    script = (REPO_ROOT / "scripts" / "setup-vps.sh").read_text(encoding="utf-8")
    assert "chmod 644 secrets/admin_password.txt" in script


def test_caddyfile_oculta_contrato_api():
    """OWASP A05 (Security Misconfiguration): /docs, /redoc y /openapi.json
    no deben servirse en produccion. Bloqueo en el edge (Caddy) como
    defensa en profundidad adicional al fix de create_app."""
    caddy = (REPO_ROOT / "Caddyfile").read_text(encoding="utf-8")
    assert "path /docs*" in caddy
    assert "/redoc*" in caddy
    assert "/openapi.json*" in caddy
    assert "respond" in caddy


def test_deploy_manual_por_release_no_auto():
    """CD agrupado por release: el despliegue solo se dispara manualmente
    (workflow_dispatch), nunca en cada merge a main. Evita redeploys
    espontaneos durante la correccion y mantiene releases versionables."""
    deploy = (REPO_ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch" in deploy
    assert "workflow_run" not in deploy
    assert "environment: production" in deploy
    assert "docker image prune" in deploy
