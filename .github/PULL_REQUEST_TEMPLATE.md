## Hito de referencia

<!-- Número de hito o issue, ej: "H9.5 — Refactoring" -->

## Descripción

<!-- Explica qué hace este PR y por qué. Contexto, problema que resuelve, decisión técnica. -->

## Cómo probar

<!-- Pasos concretos para que el reviewer verifique el cambio. Ej:
     1. `nexus.py dev`
     2. `curl -X POST ...`
     3. Verificar que ...
-->

## Checklist

### Calidad
- [ ] `ruff check .` pasa sin errores
- [ ] `ruff format --check .` pasa
- [ ] `pytest` pasa (265 tests)
- [ ] Los tests nuevos siguen TDD (RED → GREEN)
- [ ] No hay dependencias nuevas sin revisar

### Documentación y flujo
- [ ] `CHANGELOG.md` actualizado
- [ ] `README.md`, `SPEC.md`, `SECURITY.md` sincronizados si aplica
- [ ] Rama rebasada con `main`

### Seguridad
- [ ] No se exponen secretos, tokens ni datos sensibles
- [ ] Los endpoints nuevos requieren autenticación (JWT/RBAC)
- [ ] Los errores no filtran información interna (OWASP A05:2021)

## Breaking changes

- [ ] Sí: ________________________________
- [ ] No

## Dependencias nuevas

<!-- Listar cualquier paquete añadido a requirements.txt y por qué -->
