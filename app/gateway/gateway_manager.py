"""Gateway manager for IBKR TWS Gateway."""
from typing import Any
from ib_async import IB

from .docker_service import IBKRGatewayDockerService
from app.core.setup_logging import logger
from app.core.config import get_config

config = get_config()

class IBKRGatewayManager:
  """Manager for IBKR Gateway container and interactions."""

  def __init__(self) -> None:
    """Initialize the IBKR Gateway manager."""
    self.is_external = config.gateway_mode == "external"
    self.docker_service = IBKRGatewayDockerService() if not self.is_external else None
    self.is_running = False


  async def start_gateway(self) -> bool:
    """Start the IBKR Gateway container or connect to external gateway."""
    if self.is_external:
      # For external gateway, just check if we can connect
      try:
        ib = IB()
        await ib.connectAsync(config.ib_gateway_host, config.ib_gateway_port, 1111)
        if ib.isConnected():
          self.is_running = True
          logger.info(f"Connected to external IBKR Gateway at {config.ib_gateway_host}:{config.ib_gateway_port}") #noqa: E501
          ib.disconnect()
          return True
        logger.error(f"Failed to connect to external IBKR Gateway at {config.ib_gateway_host}:{config.ib_gateway_port}") #noqa: E501
      except Exception:
        logger.exception(f"Failed to connect to external IBKR Gateway at {config.ib_gateway_host}:{config.ib_gateway_port}") #noqa: E501
        return False
      else:
        return False
    else:
      # Internal gateway mode - start Docker container
      try:
        success = await self.docker_service.start_gateway()
        if success:
          self.is_running = True
          logger.debug("IBKR Gateway started successfully")
      except Exception:
        logger.exception("Failed to start gateway")
        return False
      else:
        return success

  async def stop_gateway(self) -> bool:
    """Stop the IBKR Gateway container or disconnect from external gateway."""
    if self.is_external:
      # For external gateway, just mark as not running
      self.is_running = False
      logger.debug("Disconnected from external IBKR Gateway")
      return True
    # Internal gateway mode - stop Docker container
    try:
      success = await self.docker_service.stop_gateway()
      if success:
        self.is_running = False
        logger.debug("IBKR Gateway stopped successfully")
    except Exception:
      logger.exception("Failed to stop gateway")
      return False
    else:
      return success

  async def get_gateway_status(self) -> dict[str, Any]:
    """Get the current status of the IBKR Gateway."""
    if self.is_external:
      # For external gateway, check connection
      try:
        ib = IB()
        await ib.connectAsync(config.ib_gateway_host, config.ib_gateway_port, 1111)
        is_connected = ib.isConnected()
        ib.disconnect()
      except Exception as e:
        logger.error(f"Failed to check external gateway status: {e}")
        return {
          "is_running": False,
          "mode": "external",
          "host": config.ib_gateway_host,
          "port": config.ib_gateway_port,
          "connection_status": "error",
          "error": str(e),
        }
      else:
        return {
          "is_running": is_connected,
          "mode": "external",
          "host": config.ib_gateway_host,
          "port": config.ib_gateway_port,
          "connection_status": "connected" if is_connected else "disconnected",
        }
    else:
      # Internal gateway mode - get container status
      try:
        container_status = await self.docker_service.get_container_status()
      except Exception as e:
        logger.error(f"Failed to get gateway status: {e}")
        return {
          "is_running": False,
          "mode": "internal",
          "error": str(e),
        }
      else:
        return {
          "is_running": self.is_running,
          "mode": "internal",
          "container": container_status,
        }

  async def get_gateway_logs(self, tail: int = 100) -> dict[str, Any]:
    """Get the logs from the IBKR Gateway container."""
    if self.is_external:
      return {
        "logs": ["External gateway mode - logs not available"],
        "note": "Logs are not available for external gateway connections",
      }
    logs = await self.docker_service.get_container_logs(tail)
    log_lines = [line.strip() for line in logs.split("\n") if line.strip()]
    return {"logs": log_lines}

  async def cleanup(self) -> None:
    """Cleanup resources when shutting down."""
    try:
      if self.is_running:
        await self.stop_gateway()

      # Cleanup docker service resources (only for internal mode)
      if (not self.is_external and hasattr(self, "docker_service") and
          self.docker_service and hasattr(self.docker_service, "client")):
        self.docker_service.client.close()
    except Exception as e:
      logger.error(f"Error during cleanup: {e}")
    finally:
      self.is_running = False

  def __del__(self) -> None:
    """Cleanup when the manager is destroyed."""
    if self.is_running:
      logger.warning(
        "IBKRGatewayManager destroyed while still running. "
        "Call await manager.cleanup() before destruction.",
      )
