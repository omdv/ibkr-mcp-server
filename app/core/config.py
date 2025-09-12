"""Configuration for the application."""
from typing import Any
from pydantic_settings import BaseSettings

class Config(BaseSettings):
  """Global configuration for the application."""

  model_config = {"env_prefix": "IBKR_"}

  # Common parameters
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
  def init_config(cls, **kwargs: Any) -> Config:
    """Initialize the global config with CLI parameters."""
    cls._instance = Config(**kwargs)
    return cls._instance

# Convenience functions
def get_config() -> Config:
  """Get the global config instance."""
  return ConfigManager.get_config()

def init_config(**kwargs: Any) -> Config:
  """Initialize the global config with CLI parameters."""
  return ConfigManager.init_config(**kwargs)
