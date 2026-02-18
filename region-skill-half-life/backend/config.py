"""Centralized backend configuration and environment-driven settings definitions."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	"""Application settings loaded from environment variables."""

	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

	DATABASE_URL: str = Field(default="sqlite:///./region_skill_half_life.db")
	JWT_SECRET: SecretStr = Field(default=SecretStr("replace-with-a-secure-32-char-secret"))
	ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
	OPENAI_API_KEY: SecretStr = Field(default=SecretStr("sk-replace-with-valid-openai-key"))
	ENVIRONMENT: Literal["development", "staging", "production", "test"] = Field(default="production")

	app_name: str = Field(default="Region-Based Skill Half-Life Intelligence System")
	app_version: str = Field(default="1.0.0")
	app_description: str = Field(
		default=(
			"Enterprise API for region-based skill half-life analytics, forecasting, "
			"simulation, and AI-driven intelligence delivery."
		)
	)
	debug: bool = Field(default=False)

	api_prefix: str = Field(default="/api/v1")
	frontend_origin: str = Field(default="http://localhost:5500")
	cors_origins: str = Field(default="http://localhost:5500,http://127.0.0.1:5500")

	log_level: str = Field(default="INFO")

	@field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
	@classmethod
	def validate_access_token_expiry(cls, value: int) -> int:
		"""Validate JWT access token expiry bounds in minutes."""
		if value < 5 or value > 1440:
			raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be between 5 and 1440.")
		return value

	@field_validator("JWT_SECRET")
	@classmethod
	def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
		"""Validate minimum strength requirements for JWT signing secret."""
		if len(value.get_secret_value()) < 32:
			raise ValueError("JWT_SECRET must be at least 32 characters long.")
		return value

	@field_validator("OPENAI_API_KEY")
	@classmethod
	def validate_openai_key(cls, value: SecretStr) -> SecretStr:
		"""Validate OpenAI API key shape for safe startup checks."""
		secret = value.get_secret_value()
		if not secret.startswith("sk-") or len(secret) < 10:
			raise ValueError("OPENAI_API_KEY must start with 'sk-' and be a valid key format.")
		return value

	@property
	def database_url(self) -> str:
		"""Backward-compatible lowercase accessor for database URL."""
		return self.DATABASE_URL

	@property
	def jwt_secret(self) -> str:
		"""Backward-compatible lowercase accessor for JWT secret."""
		return self.JWT_SECRET.get_secret_value()

	@property
	def access_token_expire_minutes(self) -> int:
		"""Backward-compatible lowercase accessor for token expiry."""
		return self.ACCESS_TOKEN_EXPIRE_MINUTES

	@property
	def openai_api_key(self) -> str:
		"""Backward-compatible lowercase accessor for OpenAI API key."""
		return self.OPENAI_API_KEY.get_secret_value()

	@property
	def environment(self) -> str:
		"""Backward-compatible lowercase accessor for deployment environment."""
		return self.ENVIRONMENT

	@property
	def allowed_cors_origins(self) -> List[str]:
		"""Return normalized CORS origins list."""
		raw_origins = [item.strip() for item in self.cors_origins.split(",")]
		merged = [origin for origin in raw_origins if origin]
		if self.frontend_origin and self.frontend_origin not in merged:
			merged.append(self.frontend_origin)
		return merged


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	"""Return cached settings instance for dependency injection."""
	return Settings()


config = get_settings()
