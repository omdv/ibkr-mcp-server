"""Main module for the IBKR MCP Server."""

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.api import gateway
from app.api.ibkr import ibkr_router
from app.core.setup_logging import setup_logging

logger = setup_logging()

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
  """Lifespan events for the application."""
  logger.info("Starting IBKR MCP Server...")
  try:
    success = await gateway.gateway_manager.start_gateway()
    if not success:
      logger.error("Failed to connect/start IBKR Gateway.")
  except Exception:
    logger.exception("Error with IBKR Gateway.")

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

# Include routers
app.include_router(gateway.router)
app.include_router(ibkr_router)

@app.get("/")
def read_root() -> dict:
  """Return the root endpoint."""
  return {
    "message": "Welcome to the IBKR MCP Server",
    "docs": "/docs",
    "gateway_endpoints": "/gateway",
  }

# MCP server, attached to the FastAPI app
mcp = FastApiMCP(app, exclude_tags=["gateway"])
mcp.mount()
