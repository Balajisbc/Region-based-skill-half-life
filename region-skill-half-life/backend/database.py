"""Database connectivity, session lifecycle, and persistence integration boundary."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config import get_settings


settings = get_settings()

Base = declarative_base()


def _build_engine():
	"""Create a production-safe SQLAlchemy engine focused on PostgreSQL."""
	database_url = settings.database_url
	engine_kwargs: dict[str, object] = {
		"pool_pre_ping": True,
		"pool_recycle": 1800,
	}

	if database_url.startswith("postgresql"):
		engine_kwargs.update(
			{
				"pool_size": 20,
				"max_overflow": 40,
				"pool_timeout": 30,
				"pool_use_lifo": True,
			}
		)
	elif database_url.startswith("sqlite"):
		engine_kwargs.update({"connect_args": {"check_same_thread": False}})

	return create_engine(database_url, **engine_kwargs)

engine = _build_engine()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
	"""Yield a database session for request-scoped dependency injection."""
	session = SessionLocal()
	try:
		yield session
	finally:
		session.close()


def get_db() -> Generator[Session, None, None]:
	"""FastAPI dependency provider for transactional database sessions."""
	yield from get_db_session()


def init_db() -> None:
	"""Create registered metadata tables at application startup."""
	from models import chat_model, job_market_model, report_model, user_model  # noqa: F401

	Base.metadata.create_all(bind=engine)


def check_database_connection() -> bool:
	"""Run a lightweight readiness query against the configured database."""
	try:
		with engine.connect() as connection:
			connection.execute(text("SELECT 1"))
		return True
	except SQLAlchemyError:
		return False
