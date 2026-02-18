"""Persistence model definition for platform users and access metadata."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
	from models.chat_model import ChatHistory
	from models.report_model import Report


class User(Base):
	"""User account entity for authentication and ownership relationships."""

	__tablename__ = "users"

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
	email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
	hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
	is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

	chats: Mapped[list["ChatHistory"]] = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
	reports: Mapped[list["Report"]] = relationship("Report", back_populates="user", cascade="all, delete-orphan")
