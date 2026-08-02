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
