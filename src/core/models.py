from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


user_department = Table(
    "user_department",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("department_id", Integer, ForeignKey("department.id"), primary_key=True),
)


class Department(Base):
    __tablename__ = "department"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)

    users = relationship("User", back_populates="department")
    documents = relationship("Document", back_populates="department")


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="staff")
    department_id = Column(Integer, ForeignKey("department.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    department = relationship("Department", back_populates="users", foreign_keys=[department_id])
    accessible_departments = relationship("Department", secondary=user_department)
    documents = relationship("Document", back_populates="uploader")
    audit_logs = relationship("AuditLog", back_populates="user")

    @property
    def accessible_department_ids(self) -> list[int]:
        ids = [d.id for d in self.accessible_departments]
        if self.department_id not in ids:
            ids.append(self.department_id)
        return ids


class Document(Base):
    __tablename__ = "document"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    sha256 = Column(String(64), unique=True, nullable=False)
    content_text = Column(Text, nullable=True)
    department_id = Column(Integer, ForeignKey("department.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)

    department = relationship("Department", back_populates="documents")
    uploader = relationship("User", back_populates="documents")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)

    user = relationship("User", back_populates="audit_logs")
