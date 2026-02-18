"""Persistence model for regional job market and skill volatility data."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class JobMarket(Base):
	"""Regional skill demand, compensation, and competition record."""

	__tablename__ = "job_market"
	__table_args__ = (
		CheckConstraint('"year" >= 1985 AND "year" <= 2025', name="ck_job_market_year_range"),
		Index("ix_job_market_country", "country"),
		Index("ix_job_market_city", "city"),
		Index("ix_job_market_skill", "skill"),
		Index("ix_job_market_year", "year"),
	)

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	country: Mapped[str] = mapped_column(String(100), nullable=False)
	city: Mapped[str] = mapped_column(String(120), nullable=False)
	skill: Mapped[str] = mapped_column(String(160), nullable=False)
	year: Mapped[int] = mapped_column(Integer, nullable=False)
	demand_index: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
	salary_estimate: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
	job_openings: Mapped[int] = mapped_column(Integer, nullable=False)
	competition_index: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
