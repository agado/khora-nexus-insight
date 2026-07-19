from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.auth.jwt import create_access_token
from src.core.auth.rbac import ROLE_LEVELS
from src.core.auth.security import verify_password
from src.core.models import User


async def authenticate_user(db: AsyncSession, username: str, password: str) -> dict | None:
    result = await db.execute(
        select(User)
        .where(User.username == username)
        .options(selectinload(User.accessible_departments))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return {
        "access_token": create_access_token(
            {
                "sub": user.username,
                "role": user.role,
                "role_level": ROLE_LEVELS.get(user.role, 0),
                "department_id": user.department_id,
                "accessible_departments": user.accessible_department_ids,
                "user_id": user.id,
            }
        ),
        "user_id": user.id,
    }
