import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from src.core.auth.security import verify_password
from src.core.models import Base, Department, User
from src.core.seed import (
    SEED_DEPARTMENTS,
    _build_seed_users,
    _is_production,
    _resolve_admin_password,
    seed_database,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    with session_local() as s:
        try:
            yield s
        finally:
            s.close()
            engine.dispose()


class TestSeedDatabase:
    def test_seed_creates_departments(self, session: Session):
        seed_database(session)
        depts = session.execute(select(Department)).scalars().all()
        assert len(depts) == len(SEED_DEPARTMENTS)
        names = [d.name for d in depts]
        assert "IT" in names
        assert "RRHH" in names
        assert "PM" in names

    def test_seed_creates_eight_users(self, session: Session):
        seed_database(session)
        users = session.execute(select(User)).scalars().all()
        assert len(users) == 8

    def test_seed_users_have_valid_passwords(self, session: Session):
        seed_database(session)
        for user_data in _build_seed_users():
            user = session.execute(
                select(User).where(User.username == user_data["username"])
            ).scalar_one_or_none()
            assert user is not None
            assert verify_password(user_data["password"], user.hashed_password)

    def test_seed_users_belong_to_correct_department(self, session: Session):
        seed_database(session)
        for user_data in _build_seed_users():
            user = session.execute(
                select(User).where(User.username == user_data["username"])
            ).scalar_one_or_none()
            assert user is not None
            assert user.department.name == user_data["department_name"]

    def test_seed_lead_has_correct_role(self, session: Session):
        seed_database(session)
        for name in ("lead_it", "lead_hr", "lead_pm"):
            user = session.execute(select(User).where(User.username == name)).scalar_one_or_none()
            assert user is not None
            assert user.role == "lead"

    def test_seed_ceo_has_all_departments(self, session: Session):
        seed_database(session)
        ceo = session.execute(select(User).where(User.username == "ceo")).scalar_one_or_none()
        assert ceo is not None
        ids = ceo.accessible_department_ids
        depts = session.execute(select(Department)).scalars().all()
        assert len(ids) == len(depts)

    def test_seed_staff_has_only_own_department(self, session: Session):
        seed_database(session)
        staff_it = session.execute(
            select(User).where(User.username == "staff_it")
        ).scalar_one_or_none()
        assert staff_it is not None
        assert staff_it.accessible_department_ids == [staff_it.department_id]

    def test_seed_is_idempotent(self, session: Session):
        seed_database(session)
        seed_database(session)
        users = session.execute(select(User)).scalars().all()
        assert len(users) == 8
        depts = session.execute(select(Department)).scalars().all()
        assert len(depts) == len(SEED_DEPARTMENTS)

    def test_seed_reset_clears_and_recreates(self, session: Session):
        seed_database(session)
        seed_database(session, reset=True)
        users = session.execute(select(User)).scalars().all()
        assert len(users) == 8


class TestSeedProductionMode:
    def test_is_production_true(self):
        with patch.dict(os.environ, {"ENV": "production"}):
            assert _is_production() is True

    def test_is_production_false_when_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            assert _is_production() is False

    def test_resolve_admin_password_from_env(self):
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "s3cret"}):
            assert _resolve_admin_password() == "s3cret"

    def test_resolve_admin_password_missing_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="ADMIN_PASSWORD no definida"):
                _resolve_admin_password()

    def test_resolve_admin_password_from_file(self, tmp_path):
        secret_file = tmp_path / "admin_password.txt"
        secret_file.write_text("file_secret\n")
        with patch.dict(os.environ, {"ADMIN_PASSWORD_FILE": str(secret_file)}):
            assert _resolve_admin_password() == "file_secret"

    def test_seed_prod_creates_only_admin(self, session: Session):
        with patch.dict(os.environ, {"ENV": "production", "ADMIN_PASSWORD": "prod_pw"}):
            seed_database(session)
        depts = session.execute(select(Department)).scalars().all()
        assert len(depts) == len(SEED_DEPARTMENTS)
        users = session.execute(select(User)).scalars().all()
        assert len(users) == 1
        assert users[0].username == "admin"
        assert users[0].role == "admin"
        assert verify_password("prod_pw", users[0].hashed_password)
