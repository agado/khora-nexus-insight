from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, InvalidHashError

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _ph.verify(hashed_password, plain_password)
    except (Argon2Error, InvalidHashError):
        return False
