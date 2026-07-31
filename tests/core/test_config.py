import logging
from unittest.mock import patch

import pytest

from src.core.config import check_jwt_secret


class TestCheckJwtSecret:
    def test_logs_warning_when_default_dev(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.WARNING)
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.jwt_secret = (
                "dev_secret_key_extremely_long_and_secure_for_local_testing_2026"
            )
            check_jwt_secret(env="development")
        assert len(caplog.records) >= 1
        assert "JWT_SECRET" in caplog.text

    def test_no_warning_when_custom(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.WARNING)
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.jwt_secret = "my-custom-production-secret"
            check_jwt_secret(env="development")
        assert len(caplog.records) == 0

    def test_raises_when_default_in_production(self):
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.jwt_secret = (
                "dev_secret_key_extremely_long_and_secure_for_local_testing_2026"
            )
            with pytest.raises(RuntimeError, match="JWT_SECRET"):
                check_jwt_secret(env="production")

    def test_raises_when_placeholder_in_production(self):
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.jwt_secret = "CHANGE_ME_PROD_JWT_SECRET_64chars_minimum"
            with pytest.raises(RuntimeError, match="JWT_SECRET"):
                check_jwt_secret(env="production")

    def test_no_raise_when_real_secret_in_production(self):
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.jwt_secret = "a-strong-real-production-secret-2026-sup3r-s3cr3t"
            check_jwt_secret(env="production")
