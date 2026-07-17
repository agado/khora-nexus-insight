from src.core.auth.security import hash_password, verify_password


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
