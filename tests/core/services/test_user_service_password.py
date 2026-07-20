import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.models import Base, Department, User
from src.core.services.user_service import create_user, reset_password


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        dept = Department(name="IT")
        session.add(dept)
        await session.flush()
        user = User(
            username="admin",
            hashed_password="irrelevant",
            role="admin",
            department_id=dept.id,
        )
        session.add(user)
        await session.flush()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
class TestCreateUserPasswordValidation:
    async def test_create_user_weak_password_raises(self, db_session):
        with pytest.raises(ValueError, match="8 caracteres"):
            await create_user(
                db=db_session,
                username="newuser",
                password="weak",
                role="staff",
                department_id=1,
                accessible_department_ids=[1],
            )

    async def test_create_user_strong_password_succeeds(self, db_session):
        user = await create_user(
            db=db_session,
            username="newuser",
            password="Strong1!",
            role="staff",
            department_id=1,
            accessible_department_ids=[1],
        )
        assert user is not None
        assert user.username == "newuser"


@pytest.mark.asyncio
class TestResetPasswordPasswordValidation:
    async def test_reset_password_weak_password_raises(self, db_session):
        with pytest.raises(ValueError, match="8 caracteres"):
            await reset_password(db_session, user_id=1, new_password="weak")

    async def test_reset_password_strong_password_succeeds(self, db_session):
        ok = await reset_password(db_session, user_id=1, new_password="Strong1!")
        assert ok is True
