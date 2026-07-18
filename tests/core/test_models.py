import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.core.models import AuditLog, Base, Department, Document, User, user_department


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


@pytest.fixture
def dept_it(session: Session) -> Department:
    dept = Department(name="IT")
    session.add(dept)
    session.commit()
    return dept


@pytest.fixture
def user_admin(session: Session, dept_it: Department) -> User:
    user = User(
        username="admin",
        hashed_password="hashed_admin",
        role="admin",
        department_id=dept_it.id,
    )
    session.add(user)
    session.commit()
    return user


class TestDepartment:
    def test_create_department(self, session: Session):
        dept = Department(name="RRHH")
        session.add(dept)
        session.commit()
        assert dept.id is not None
        assert dept.name == "RRHH"

    def test_department_unique_name(self, session: Session, dept_it: Department):
        dept = Department(name="IT")
        session.add(dept)
        with pytest.raises(IntegrityError):
            session.commit()


class TestUser:
    def test_create_user(self, session: Session, dept_it: Department):
        user = User(
            username="test_user",
            hashed_password="hashed_test",
            role="staff",
            department_id=dept_it.id,
        )
        session.add(user)
        session.commit()
        assert user.id is not None
        assert user.username == "test_user"
        assert user.role == "staff"

    def test_user_unique_username(self, session: Session, dept_it: Department, user_admin: User):
        user = User(
            username="admin",
            hashed_password="another_hash",
            role="staff",
            department_id=dept_it.id,
        )
        session.add(user)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_user_belongs_to_department(self, user_admin: User, dept_it: Department):
        assert user_admin.department_id == dept_it.id
        assert user_admin.department.name == "IT"

    def test_user_created_at_auto(self, user_admin: User):
        assert user_admin.created_at is not None

    def test_user_accessible_departments_m2m(self, session: Session, dept_it: Department):
        hr = Department(name="RRHH")
        session.add(hr)
        session.commit()
        user = User(
            username="cross_user",
            hashed_password="hash",
            role="staff",
            department_id=dept_it.id,
        )
        session.add(user)
        session.commit()
        session.execute(user_department.insert().values(user_id=user.id, department_id=hr.id))
        session.commit()
        session.refresh(user)
        assert len(user.accessible_departments) == 1
        assert user.accessible_departments[0].name == "RRHH"

    def test_accessible_department_ids_includes_primary(
        self, session: Session, dept_it: Department
    ):
        hr = Department(name="RRHH")
        session.add(hr)
        session.commit()
        user = User(
            username="multi_user",
            hashed_password="hash",
            role="staff",
            department_id=dept_it.id,
        )
        session.add(user)
        session.commit()
        session.execute(user_department.insert().values(user_id=user.id, department_id=hr.id))
        session.commit()
        session.refresh(user)
        ids = user.accessible_department_ids
        assert dept_it.id in ids
        assert hr.id in ids
        assert len(ids) == 2


class TestDocument:
    def test_create_document(self, session: Session, dept_it: Department, user_admin: User):
        doc = Document(
            filename="test.txt",
            sha256="abc123",
            content_text="Hello world",
            department_id=dept_it.id,
            uploaded_by=user_admin.id,
        )
        session.add(doc)
        session.commit()
        assert doc.id is not None
        assert doc.filename == "test.txt"
        assert doc.sha256 == "abc123"
        assert doc.content_text == "Hello world"

    def test_document_unique_sha256(self, session: Session, dept_it: Department, user_admin: User):
        doc1 = Document(
            filename="doc1.txt",
            sha256="unique_hash",
            department_id=dept_it.id,
            uploaded_by=user_admin.id,
        )
        session.add(doc1)
        session.commit()
        doc2 = Document(
            filename="doc2.txt",
            sha256="unique_hash",
            department_id=dept_it.id,
            uploaded_by=user_admin.id,
        )
        session.add(doc2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_document_relationships(self, session: Session, dept_it: Department, user_admin: User):
        doc = Document(
            filename="rel.txt",
            sha256="rel_hash",
            department_id=dept_it.id,
            uploaded_by=user_admin.id,
        )
        session.add(doc)
        session.commit()
        assert doc.uploader.username == "admin"
        assert doc.department.name == "IT"

    def test_document_content_text_nullable(
        self, session: Session, dept_it: Department, user_admin: User
    ):
        doc = Document(
            filename="empty.txt",
            sha256="empty_hash",
            department_id=dept_it.id,
            uploaded_by=user_admin.id,
        )
        session.add(doc)
        session.commit()
        assert doc.content_text is None


class TestAuditLog:
    def test_create_audit_log(self, session: Session, user_admin: User):
        log = AuditLog(
            action="login",
            user_id=user_admin.id,
        )
        session.add(log)
        session.commit()
        assert log.id is not None
        assert log.action == "login"
        assert log.user_id == user_admin.id

    def test_audit_log_timestamp_auto(self, session: Session, user_admin: User):
        log = AuditLog(action="upload", user_id=user_admin.id)
        session.add(log)
        session.commit()
        assert log.timestamp is not None

    def test_audit_log_metadata_json(self, session: Session, user_admin: User):
        log = AuditLog(
            action="query",
            user_id=user_admin.id,
            metadata_={"query": "test", "model": "qwen"},
        )
        session.add(log)
        session.commit()
        assert log.metadata_["query"] == "test"
