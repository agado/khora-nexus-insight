import argparse
import asyncio
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.auth.security import hash_password
from src.core.models import Base, Department, User

SEED_DEPARTMENTS = [
    {"name": "IT"},
    {"name": "RRHH"},
    {"name": "PM"},
]

SEED_USERS = [
    {
        "username": "admin",
        "password": "admin123",
        "role": "admin",
        "department_name": "IT",
        "is_cross_department": False,
    },
    {
        "username": "staff_it",
        "password": "staff123",
        "role": "staff",
        "department_name": "IT",
        "is_cross_department": False,
    },
    {
        "username": "staff_hr",
        "password": "staff123",
        "role": "staff",
        "department_name": "RRHH",
        "is_cross_department": False,
    },
    {
        "username": "staff_pm",
        "password": "staff123",
        "role": "staff",
        "department_name": "PM",
        "is_cross_department": False,
    },
    {
        "username": "ceo",
        "password": "ceo123",
        "role": "admin",
        "department_name": "IT",
        "is_cross_department": True,
    },
]


def _get_department_id(session: Session, department_name: str) -> int:
    stmt = select(Department).where(Department.name == department_name)
    dept = session.execute(stmt).scalar_one_or_none()
    if dept is None:
        dept = Department(name=department_name)
        session.add(dept)
        session.flush()
    return dept.id


def _is_production() -> bool:
    return os.environ.get("ENV", "").lower() == "production"


def _resolve_admin_password() -> str:
    secret_file = os.environ.get("ADMIN_PASSWORD_FILE")
    if secret_file:
        with open(secret_file) as f:
            return f.read().strip()
    pw = os.environ.get("ADMIN_PASSWORD")
    if pw:
        return pw
    msg = (
        "ADMIN_PASSWORD no definida. "
        "En producción, defínela vía Docker secret (ADMIN_PASSWORD_FILE) "
        "o variable de entorno (ADMIN_PASSWORD)."
    )
    raise RuntimeError(msg)


def _upsert_user(session: Session, user_data: dict) -> None:
    existing = session.execute(
        select(User).where(User.username == user_data["username"])
    ).scalar_one_or_none()
    if existing:
        return
    dept_id = _get_department_id(session, user_data["department_name"])
    user = User(
        username=user_data["username"],
        hashed_password=hash_password(user_data["password"]),
        role=user_data["role"],
        department_id=dept_id,
        is_cross_department=user_data["is_cross_department"],
    )
    session.add(user)


def seed_database(session: Session, reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(bind=session.get_bind())
        Base.metadata.create_all(bind=session.get_bind())

    for dept_data in SEED_DEPARTMENTS:
        existing = session.execute(
            select(Department).where(Department.name == dept_data["name"])
        ).scalar_one_or_none()
        if existing is None:
            session.add(Department(**dept_data))
    session.flush()

    if _is_production():
        admin_pw = _resolve_admin_password()
        _upsert_user(
            session,
            {
                "username": "admin",
                "password": admin_pw,
                "role": "admin",
                "department_name": "IT",
                "is_cross_department": False,
            },
        )
    else:
        for user_data in SEED_USERS:
            _upsert_user(session, user_data)
    session.commit()


async def _run_async(reset: bool = False) -> None:
    from src.core.database import async_session

    async with async_session() as session:
        await session.run_sync(lambda s: seed_database(s, reset=reset))


def main() -> None:
    parser = argparse.ArgumentParser(description="Puebla la base de datos con datos iniciales")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Elimina todas las tablas y las vuelve a crear antes de insertar los datos",
    )
    args = parser.parse_args()
    asyncio.run(_run_async(reset=args.reset))
    print("Base de datos poblada correctamente.")


if __name__ == "__main__":
    main()
