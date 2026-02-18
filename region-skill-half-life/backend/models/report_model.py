"""Persistence model for generated analytics reports and export metadata."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
	from models.user_model import User


class Report(Base):
	"""Generated report entity mapped to a user account."""

	__tablename__ = "reports"

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	user_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("users.id", ondelete="CASCADE"),
		nullable=False,
		index=True,
	)
	country: Mapped[str] = mapped_column(String(100), nullable=False)
	city: Mapped[str] = mapped_column(String(120), nullable=False)
	skill: Mapped[str] = mapped_column(String(160), nullable=False)
	half_life: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
	stability_score: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
	risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
	report_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

	user: Mapped["User"] = relationship("User", back_populates="reports")
