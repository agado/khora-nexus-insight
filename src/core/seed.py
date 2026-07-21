import argparse
import asyncio
import os

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.orm import Session

from src.core.auth.security import hash_password
from src.core.config import settings
from src.core.models import Base, Department, User, user_department

SEED_DEPARTMENTS = [
    {"name": "IT"},
    {"name": "RRHH"},
    {"name": "PM"},
    {"name": "Marketing"},
    {"name": "Atención al Cliente"},
    {"name": "Finanzas"},
]


def _build_seed_users() -> list[dict]:
    users = [
        {
            "username": settings.admin_username,
            "password": "admin123",
            "role": "admin",
            "department_name": "IT",
            "accessible_department_names": [
                "IT",
                "RRHH",
                "PM",
                "Marketing",
                "Atención al Cliente",
                "Finanzas",
            ],
        },
        {
            "username": "ceo",
            "password": "ceo123",
            "role": "admin",
            "department_name": "IT",
            "accessible_department_names": [
                "IT",
                "RRHH",
                "PM",
                "Marketing",
                "Atención al Cliente",
                "Finanzas",
            ],
        },
        {
            "username": "lead_it",
            "password": "lead123",
            "role": "lead",
            "department_name": "IT",
            "accessible_department_names": ["IT"],
        },
        {
            "username": "lead_hr",
            "password": "lead123",
            "role": "lead",
            "department_name": "RRHH",
            "accessible_department_names": ["RRHH"],
        },
        {
            "username": "lead_pm",
            "password": "lead123",
            "role": "lead",
            "department_name": "PM",
            "accessible_department_names": ["PM"],
        },
        {
            "username": "staff_it",
            "password": "staff123",
            "role": "staff",
            "department_name": "IT",
            "accessible_department_names": ["IT"],
        },
        {
            "username": "staff_hr",
            "password": "staff123",
            "role": "staff",
            "department_name": "RRHH",
            "accessible_department_names": ["RRHH"],
        },
        {
            "username": "staff_pm",
            "password": "staff123",
            "role": "staff",
            "department_name": "PM",
            "accessible_department_names": ["PM"],
        },
    ]
    return users


def _get_department_id(session: Session, department_name: str) -> int:
    stmt = select(Department).where(Department.name == department_name)
    dept = session.execute(stmt).scalar_one_or_none()
    if dept is None:
        dept = Department(name=department_name)
        session.add(dept)
        session.flush()
    return dept.id


def _is_production() -> bool:
    return os.environ.get("NEXUS_ENV", "").lower() == "production"


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
    dept_id = _get_department_id(session, user_data["department_name"])
    if existing:
        existing.department_id = dept_id
        existing.role = user_data["role"]
        user = existing
    else:
        user = User(
            username=user_data["username"],
            hashed_password=hash_password(user_data["password"]),
            role=user_data["role"],
            department_id=dept_id,
        )
        session.add(user)
    session.flush()

    session.execute(sa_delete(user_department).where(user_department.c.user_id == user.id))
    for dept_name in user_data.get("accessible_department_names", [user_data["department_name"]]):
        access_dept_id = _get_department_id(session, dept_name)
        session.execute(
            user_department.insert().values(user_id=user.id, department_id=access_dept_id)
        )


def seed_database(session: Session, reset: bool = False) -> None:
    if not settings.admin_username:
        raise RuntimeError("ADMIN_USERNAME no puede estar vacío")
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
                "username": settings.admin_username,
                "password": admin_pw,
                "role": "admin",
                "department_name": "IT",
                "accessible_department_names": ["IT"],
            },
        )
    else:
        for user_data in _build_seed_users():
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
