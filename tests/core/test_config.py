import logging
from unittest.mock import patch

import pytest

from src.core.config import check_jwt_secret


class TestCheckJwtSecret:
    def test_logs_warning_when_default(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.WARNING)
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.jwt_secret = "dev_secret_key_extremely_long_and_secure_for_local_testing_2026"
            check_jwt_secret()
        assert len(caplog.records) >= 1
        assert "JWT_SECRET" in caplog.text

    def test_no_warning_when_custom(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.WARNING)
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.jwt_secret = "my-custom-production-secret"
            check_jwt_secret()
        assert len(caplog.records) == 0
