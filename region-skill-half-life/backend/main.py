"""Backend API application entrypoint for the Region-Based Skill Half-Life Intelligence System."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import Settings, get_settings
from database import check_database_connection, init_db
from dependencies import get_db
from routes.analytics_routes import router as analytics_router
from routes.auth_routes import router as auth_router
from routes.chat_routes import router as chat_router
from routes.comparison_routes import router as comparison_router
from routes.region_routes import router as region_router
from routes.report_routes import router as report_router
from routes.simulation_routes import router as simulation_router


def configure_logging(settings: Settings) -> logging.Logger:
	"""Configure application-wide structured logging."""
	logging.basicConfig(
		level=getattr(logging, settings.log_level.upper(), logging.INFO),
		format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
	)
	logger = logging.getLogger("region-skill-half-life")
	logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
	return logger


settings = get_settings()
logger = configure_logging(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Manage startup and shutdown lifecycle events."""
	logger.info("Starting server | app=%s | version=%s", settings.app_name, settings.app_version)
	init_db()
	logger.info("Database metadata initialization completed")
	app.state.started_at = time.time()
	app.state.instance_id = str(uuid.uuid4())
	app.state.environment = settings.environment
	yield
	logger.info("Shutting down server | app=%s", settings.app_name)


def add_cors_middleware(app: FastAPI, app_settings: Settings) -> None:
	"""Attach CORS middleware for frontend interaction."""
	app.add_middleware(
		CORSMiddleware,
		allow_origins=app_settings.allowed_cors_origins,
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)


def add_request_context_middleware(app: FastAPI) -> None:
	"""Attach request context middleware for tracing and observability."""

	@app.middleware("http")
	async def inject_request_context(request: Request, call_next: Callable):
		request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
		request.state.request_id = request_id
		start = time.perf_counter()

		response = await call_next(request)

		elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
		response.headers["X-Request-ID"] = request_id
		response.headers["X-Response-Time-ms"] = str(elapsed_ms)

		logger.info(
			"request_complete | request_id=%s | method=%s | path=%s | status=%s | latency_ms=%s",
			request_id,
			request.method,
			request.url.path,
			response.status_code,
			elapsed_ms,
		)
		return response


def register_exception_handlers(app: FastAPI) -> None:
	"""Register global exception handlers."""

	@app.exception_handler(StarletteHTTPException)
	async def http_exception_handler(request: Request, exc: StarletteHTTPException):
		request_id = getattr(request.state, "request_id", "unknown")
		return JSONResponse(
			status_code=exc.status_code,
			content={
				"error": {
					"type": "http_error",
					"message": exc.detail,
					"request_id": request_id,
				}
			},
		)

	@app.exception_handler(RequestValidationError)
	async def validation_exception_handler(request: Request, exc: RequestValidationError):
		request_id = getattr(request.state, "request_id", "unknown")
		return JSONResponse(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			content={
				"error": {
					"type": "validation_error",
					"message": "Request payload validation failed.",
					"details": exc.errors(),
					"request_id": request_id,
				}
			},
		)

	@app.exception_handler(Exception)
	async def unhandled_exception_handler(request: Request, exc: Exception):
		request_id = getattr(request.state, "request_id", "unknown")
		logger.exception("unhandled_exception | request_id=%s", request_id)
		return JSONResponse(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			content={
				"error": {
					"type": "internal_server_error",
					"message": "An unexpected error occurred.",
					"request_id": request_id,
				}
			},
		)


def register_routes(app: FastAPI, app_settings: Settings) -> None:
	"""Register all feature routers with a shared API prefix."""
	app.include_router(auth_router, prefix=app_settings.api_prefix)
	app.include_router(analytics_router, prefix=app_settings.api_prefix)
	app.include_router(region_router, prefix=app_settings.api_prefix)
	app.include_router(chat_router, prefix=app_settings.api_prefix)
	app.include_router(report_router, prefix=app_settings.api_prefix)
	app.include_router(comparison_router, prefix=app_settings.api_prefix)
	app.include_router(simulation_router, prefix=app_settings.api_prefix)


def create_app() -> FastAPI:
	"""Create and configure FastAPI application instance."""
	app = FastAPI(
		title=settings.app_name,
		version=settings.app_version,
		description=settings.app_description,
		lifespan=lifespan,
		docs_url="/docs",
		redoc_url="/redoc",
		openapi_url=f"{settings.api_prefix}/openapi.json",
	)

	add_cors_middleware(app, settings)
	add_request_context_middleware(app)
	register_exception_handlers(app)
	register_routes(app, settings)

	@app.get("/", tags=["system"], summary="Root endpoint")
	def root() -> dict[str, str]:
		return {
			"service": settings.app_name,
			"version": settings.app_version,
			"status": "running",
		}

	@app.get("/health", tags=["system"], summary="Service health check")
	def health_check(db: Session = Depends(get_db)) -> dict[str, object]:
		"""Return runtime and dependency health status."""
		_ = db
		db_ok = check_database_connection()
		uptime_seconds = int(time.time() - app.state.started_at)

		status_text = "healthy" if db_ok else "degraded"
		status_code = "ok" if db_ok else "db_unreachable"

		return {
			"status": status_text,
			"code": status_code,
			"environment": app.state.environment,
			"version": settings.app_version,
			"instance_id": app.state.instance_id,
			"database": {"connected": db_ok},
			"uptime_seconds": uptime_seconds,
		}

	return app


app = create_app()
