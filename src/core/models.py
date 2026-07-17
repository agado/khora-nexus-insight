from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


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
    is_cross_department = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    department = relationship("Department", back_populates="users")
    documents = relationship("Document", back_populates="uploader")
    audit_logs = relationship("AuditLog", back_populates="user")


class Document(Base):
    __tablename__ = "document"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    sha256 = Column(String(64), unique=True, nullable=False)
    content_text = Column(Text, nullable=True)
    department_id = Column(Integer, ForeignKey("department.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

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
