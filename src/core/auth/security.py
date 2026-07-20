import re

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, InvalidHashError

_ph = PasswordHasher()

MIN_PASSWORD_LENGTH = 8


def validate_password_complexity(password: str) -> None:
    errors: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"al menos {MIN_PASSWORD_LENGTH} caracteres")
    if not re.search(r"[A-Z]", password):
        errors.append("una may\xfascula")
    if not re.search(r"[a-z]", password):
        errors.append("una min\xfascula")
    if not re.search(r"\d", password):
        errors.append("un d\xedgito")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("un car\xe1cter especial")
    if errors:
        raise ValueError("La contrase\xf1a debe tener " + ", ".join(errors) + ".")


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _ph.verify(hashed_password, plain_password)
    except (Argon2Error, InvalidHashError):
        return False
