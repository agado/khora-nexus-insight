from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.auth.jwt import verify_token
from src.core.auth.security import hash_password
from src.core.models import User
from src.core.services.auth_service import authenticate_user


class TestAuthenticateUser:
    @pytest.mark.asyncio
    async def test_success_returns_token_with_user_id_and_accessible_departments(self):
        user = User(
            id=1,
            username="admin",
            hashed_password=hash_password("admin123"),
            role="admin",
            department_id=1,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        token = await authenticate_user(mock_db, "admin", "admin123")

        assert token is not None
        payload = verify_token(token)
        assert payload["sub"] == "admin"
        assert payload["role"] == "admin"
        assert payload["department_id"] == 1
        assert isinstance(payload["accessible_departments"], list)
        assert 1 in payload["accessible_departments"]
        assert payload["user_id"] == 1

    @pytest.mark.asyncio
    async def test_wrong_password_returns_none(self):
        user = User(
            username="admin",
            hashed_password=hash_password("admin123"),
            role="admin",
            department_id=1,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        token = await authenticate_user(mock_db, "admin", "wrong_password")

        assert token is None

    @pytest.mark.asyncio
    async def test_nonexistent_user_returns_none(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        token = await authenticate_user(mock_db, "noone", "any_password")

        assert token is None
