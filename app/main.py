"""Main module for the IBKR MCP Server."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.api import gateway
from app.api.ibkr import ibkr_router
from app.core.auth import AuthMiddleware
from app.core.config import get_config
from app.core.setup_logging import setup_logging

logger = setup_logging()

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
  """Lifespan events for the application."""
  logger.info("Starting IBKR MCP Server...")

  # Only start internal gateway during startup, external gateway is handled on-demand
  if not gateway.gateway_manager.is_external:
    try:
      success = await gateway.gateway_manager.start_gateway()
      if not success:
        logger.error("Failed to start internal IBKR Gateway.")
    except Exception:
      logger.exception("Error starting internal IBKR Gateway.")
  else:
    logger.info("External gateway mode - connection will be established on-demand")

  yield

  # Shutdown
  logger.info("Shutting down IBKR MCP Server...")

  # Cleanup gateway
  try:
    await gateway.gateway_manager.cleanup()
  except Exception:
    logger.exception("Error during cleanup.")


app = FastAPI(
  title="IBKR MCP Server",
  description="Interactive Brokers MCP Server",
  version="1.0.0",
  docs_url="/docs",
  lifespan=lifespan,
)

# Get configuration
config = get_config()

# Add CORS middleware
logger.debug(f"CORS allowed origins: {config.get_cors_origins_list()}")
app.add_middleware(
  CORSMiddleware,
  allow_origins=config.get_cors_origins_list(),
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(gateway.router)
app.include_router(ibkr_router)

@app.get("/")
def read_root() -> dict:
  """Return the root endpoint."""
  return {
    "message": "Welcome to the IBKR MCP Server",
    "docs": "/docs",
    "status": "/gateway/status",
  }

# MCP server, attached to the FastAPI app
mcp = FastApiMCP(app, exclude_tags=["gateway"])
mcp.mount()
