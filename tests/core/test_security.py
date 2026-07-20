import pytest

from src.core.auth.security import (
    hash_password,
    validate_password_complexity,
    verify_password,
)


class TestValidatePasswordComplexity:
    def test_valid_password_passes(self):
        validate_password_complexity("Abcdef1!")

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="8 caracteres"):
            validate_password_complexity("Ab1!")

    def test_no_uppercase_raises(self):
        with pytest.raises(ValueError, match="may\xfascula"):
            validate_password_complexity("abcdef1!")

    def test_no_lowercase_raises(self):
        with pytest.raises(ValueError, match="min\xfascula"):
            validate_password_complexity("ABCDEF1!")

    def test_no_digit_raises(self):
        with pytest.raises(ValueError, match="d\xedgito"):
            validate_password_complexity("Abcdefgh!")

    def test_no_special_raises(self):
        with pytest.raises(ValueError, match="especial"):
            validate_password_complexity("Abcdefgh1")


class TestHashPassword:
    def test_hash_returns_different_string(self):
        hashed = hash_password("admin123")
        assert hashed != "admin123"
        assert hashed.startswith("$argon2id$")

    def test_verify_correct_password(self):
        hashed = hash_password("admin123")
        assert verify_password("admin123", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("admin123")
        assert verify_password("wrong", hashed) is False

    def test_verify_invalid_hash_returns_false(self):
        assert verify_password("admin123", "invalid_hash") is False
