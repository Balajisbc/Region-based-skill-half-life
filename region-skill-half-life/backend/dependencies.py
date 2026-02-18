"""Shared dependency providers and injectable backend application dependencies."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from database import get_db as database_get_db


def get_db() -> Generator[Session, None, None]:
	"""Expose database session dependency for FastAPI route handlers."""
	yield from database_get_db()
