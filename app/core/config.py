"""Configuration for the application."""
import secrets
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Config(BaseSettings):
  """Global configuration for the application."""

  model_config = {"env_prefix": "IBKR_"}

  # Common parameters
  application_host: str = "127.0.0.1"  # IBKR_APPLICATION_HOST
  application_port: int = 8000  # IBKR_APPLICATION_PORT
  log_level: str = "INFO"       # IBKR_LOG_LEVEL
  gateway_mode: str = "internal"  # IBKR_GATEWAY_MODE ("internal" or "external")

  # Internal gateway parameters (only needed when gateway_mode="internal")
  ib_gateway_username: str | None = None  # IBKR_IB_GATEWAY_USERNAME
  ib_gateway_password: str | None = None  # IBKR_IB_GATEWAY_PASSWORD
  ib_command_server_port: int = 7462      # IBKR_IB_COMMAND_SERVER_PORT

  # External gateway parameters (only needed when gateway_mode="external")
  ib_gateway_host: str = "localhost"  # IBKR_IB_GATEWAY_HOST
  ib_gateway_port: int = 8888         # IBKR_IB_GATEWAY_PORT

  # Non-essential parameters
  enable_file_logging: bool = False   # IBKR_ENABLE_FILE_LOGGING
  log_file_path: str = "logs/app.log"  # IBKR_LOG_FILE_PATH

  # Security parameters
  cors_allowed_origins: list[str] = ["*"]  # IBKR_CORS_ALLOWED_ORIGINS (comma-separated)
  auth_token: str | None = None  # IBKR_AUTH_TOKEN
  _generated_token: str | None = None  # Internal field for generated token

  @field_validator("cors_allowed_origins", mode="before")
  @classmethod
  def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
    """Parse comma-separated CORS origins from environment variable."""
    if isinstance(v, str):
      return [origin.strip() for origin in v.split(",") if origin.strip()]
    return v if isinstance(v, list) else ["*"]

  def get_effective_auth_token(self) -> str:
    """Get the effective auth token, generating one if none provided."""
    if self.auth_token:
      return self.auth_token

    if not self._generated_token:
      self._generated_token = secrets.token_urlsafe(32)

    return self._generated_token

  def is_token_generated(self) -> bool:
    """Check if the auth token was auto-generated."""
    return self.auth_token is None

class ConfigManager:
  """Singleton class to manage the global config."""

  _instance: Config = None

  @classmethod
  def get_config(cls) -> Config:
    """Get the global config instance."""
    if cls._instance is None:
      cls._instance = Config()
    return cls._instance

  @classmethod
  def init_config(cls, **kwargs: str | int | bool | None) -> Config:
    """Initialize the global config with CLI parameters."""
    cls._instance = Config(**kwargs)
    return cls._instance

# Convenience functions
def get_config() -> Config:
  """Get the global config instance."""
  return ConfigManager.get_config()

def init_config(**kwargs: str | int | bool | None) -> Config:
  """Initialize the global config with CLI parameters."""
  return ConfigManager.init_config(**kwargs)
