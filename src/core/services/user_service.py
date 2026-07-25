from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.auth.rbac import ROLE_LEVELS
from src.core.auth.security import hash_password, validate_password_complexity
from src.core.models import Department, User, user_department

VALID_ROLES = frozenset(ROLE_LEVELS.keys())


async def list_users(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(User).options(selectinload(User.department)))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "department_name": u.department.name if u.department else "",
            "created_at": u.created_at.isoformat() if u.created_at else "",
        }
        for u in users
    ]


async def get_departments(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Department).order_by(Department.name))
    depts = result.scalars().all()
    return [{"id": d.id, "name": d.name} for d in depts]


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    role: str,
    department_id: int,
    accessible_department_ids: list[int],
) -> User:
    validate_password_complexity(password)
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Valid: {sorted(VALID_ROLES)}")
    if not accessible_department_ids:
        raise ValueError("Debe seleccionar al menos un departamento accesible")

    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise ValueError("Username already exists")

    user = User(
        username=username,
        hashed_password=hash_password(password),
        role=role,
        department_id=department_id,
    )
    db.add(user)
    await db.flush()

    for dept_id in accessible_department_ids:
        await db.execute(user_department.insert().values(user_id=user.id, department_id=dept_id))
    await db.flush()
    return user


async def delete_user(db: AsyncSession, user_id: int, current_user_id: int) -> bool:
    if user_id == current_user_id:
        raise ValueError("Cannot delete yourself")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False

    await db.delete(user)
    await db.flush()
    return True


async def reset_password(db: AsyncSession, user_id: int, new_password: str) -> bool:
    validate_password_complexity(new_password)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False

    user.hashed_password = hash_password(new_password)
    await db.flush()
    return True


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.department), selectinload(User.accessible_departments))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def update_user(
    db: AsyncSession,
    user_id: int,
    username: str,
    role: str,
    department_id: int,
    accessible_department_ids: list[int],
) -> User:
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Valid: {sorted(VALID_ROLES)}")
    if not accessible_department_ids:
        raise ValueError("Debe seleccionar al menos un departamento accesible")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    existing = await db.execute(select(User).where(User.username == username, User.id != user_id))
    if existing.scalar_one_or_none():
        raise ValueError("Username already exists")

    user.username = username
    user.role = role
    user.department_id = department_id

    await db.execute(sa_delete(user_department).where(user_department.c.user_id == user_id))
    for dept_id in accessible_department_ids:
        await db.execute(user_department.insert().values(user_id=user_id, department_id=dept_id))

    await db.flush()
    return user
