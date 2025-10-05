"""Authentication middleware for the application."""

import secrets
from fastapi import FastAPI, Request, status, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import get_config

# Define whitelisted paths in a set for efficient lookups
PUBLIC_PATHS = {
  "/",
  "/gateway/status",
  "/docs",
}

class AuthMiddleware(BaseHTTPMiddleware):
  """Authentication middleware that protects all endpoints except public ones."""

  def __init__(self, app: FastAPI) -> None:
    """Initialize the authentication middleware."""
    super().__init__(app)

  async def dispatch(self, request: Request, call_next) -> Response: #noqa: ANN001
    """Process the request and check authentication."""
    if request.url.path in PUBLIC_PATHS:
      return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
      return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Missing or invalid authorization header"},
        headers={"WWW-Authenticate": "Bearer"},
      )

    token = auth_header.split(" ")[1]

    config = get_config()
    expected_token = config.get_effective_auth_token()

    if not secrets.compare_digest(token, expected_token):
      return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid authentication token"},
        headers={"WWW-Authenticate": "Bearer"},
      )

    return await call_next(request)
