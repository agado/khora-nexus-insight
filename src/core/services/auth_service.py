from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.jwt import create_access_token
from src.core.auth.security import verify_password
from src.core.models import User


async def authenticate_user(db: AsyncSession, username: str, password: str) -> str | None:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return create_access_token(
        {
            "sub": user.username,
            "role": user.role,
            "department_id": user.department_id,
            "is_cross_department": user.is_cross_department,
        }
    )
