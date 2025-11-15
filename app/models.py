"""SQLAlchemy models for the Eidolon investigative toolkit."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(512), nullable=False)
    size = Column(Integer, nullable=False)
    md5 = Column(String(32), nullable=False)
    sha1 = Column(String(40), nullable=False)
    sha256 = Column(String(64), nullable=False)
    mime_type = Column(String(255), nullable=True)
    score = Column(Integer, nullable=False, default=0)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    findings = relationship(
        "Finding",
        back_populates="scan",
        cascade="all, delete-orphan",
        order_by="Finding.id",
    )


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(128), nullable=True)
    severity = Column(String(32), nullable=False)
    description = Column(Text, nullable=True)

    scan = relationship("Scan", back_populates="findings")


class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    base_url = Column(String(1024), nullable=False)
    auth_type = Column(String(64), nullable=True)
    api_key = Column(String(1024), nullable=True)
    headers_json = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    last_tested_at = Column(DateTime, nullable=True)
    last_test_status = Column(String(32), nullable=True)
    last_test_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
