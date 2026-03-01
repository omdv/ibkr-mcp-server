# IBKR MCP Server - Agent Instructions

## Project Overview

This is a FastAPI-based MCP (Model Context Protocol) server for Interactive Brokers (IBKR) trading operations. The server manages an IBKR Gateway Docker container and exposes trading functionality through REST API and MCP endpoints.

## Running the Project

### Using the provided script
```bash
./run.sh
```

This script:
1. Installs dependencies using `uv sync --reinstall`
2. Starts the IBKR MCP Server on port 8000
3. Automatically starts the IBKR Gateway Docker container

### Manual execution
```bash
uv run python main.py --ib-gateway-tradingmode=paper
```

### Using uv

This project uses **uv** for Python package management:

```bash
# Install dependencies
uv sync

# Install with reinstall
uv sync --reinstall

# Run Python with uv
uv run python main.py
```

## Environment Configuration

The project uses environment variables loaded from `.env` file.

### Required variables
- `IB_GATEWAY_USERNAME` - IBKR Gateway username
- `IB_GATEWAY_PASSWORD` - IBKR Gateway password

### Optional variables
- `ENABLE_FILE_LOGGING=true` - Enable file logging (default: false)
- `LOG_FILE_PATH=logs/app.log` - Log file location
- `LOG_LEVEL=INFO` - Log level (DEBUG, INFO, WARNING, ERROR)
- `IB_CONNECTION_TIMEOUT=20` - Connection timeout in seconds
- `IB_REQUEST_TIMEOUT=30` - Request timeout in seconds

### How environment is loaded
The app uses `python-dotenv` to load variables from `.env`. In code:
```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env file
```

## Project Structure

```
ibkr-mcp-server/
├── app/
│   ├── api/           # API endpoints
│   │   ├── gateway.py # Gateway management
│   │   └── ibkr/      # IBKR trading endpoints
│   ├── core/          # Core configuration
│   │   ├── config.py  # Settings management
│   │   └── setup_logging.py
│   ├── gateway/       # Docker container management
│   ├── models/        # Data models
│   └── services/     # Business logic
├── logs/              # Application logs (when enabled)
├── main.py            # Entry point
└── run.sh             # Startup script
```

## Important Files

- `app/core/config.py` - Configuration settings
- `app/core/setup_logging.py` - Logging setup (uses Loguru)
- `app/gateway/docker_service.py` - IBKR Gateway Docker management
- `.env` - Environment variables (not committed to git)

## API Endpoints

- `http://localhost:8000/` - Root
- `http://localhost:8000/docs` - Swagger documentation
- `http://localhost:8000/mcp` - MCP server

## Logs

- **Application logs**: `logs/app.log` (when `ENABLE_FILE_LOGGING=true`)
- **Console output**: stdout when running
- **Gateway container logs**: `curl http://localhost:8000/gateway/logs`

## Dependencies

Managed via `pyproject.toml` and installed with uv:
- fastapi
- uvicorn
- loguru
- ib-async
- docker
- pandas
- pydantic-settings

## Testing Framework

This project uses **pytest** for API testing.

### Running Tests

```bash
# Install test dependencies
uv sync --group dev

# Run all tests
uv run pytest tests/test_api.py -v

# Run specific test categories
uv run pytest tests/test_api.py -v -m gateway
uv run pytest tests/test_api.py -v -m connection
uv run pytest tests/test_api.py -v -m account
uv run pytest tests/test_api.py -v -m market_data
uv run pytest tests/test_api.py -v -m contracts
uv run pytest tests/test_api.py -v -m scanners
```

### Test Categories

Tests are organized by marker:
- `@pytest.mark.gateway` - Gateway endpoints
- `@pytest.mark.connection` - Connection endpoints
- `@pytest.mark.account` - Account endpoints
- `@pytest.mark.market_data` - Market data endpoints
- `@pytest.mark.contracts` - Contract endpoints
- `@pytest.mark.scanners` - Scanner endpoints
- `@pytest.mark.trading` - Trading endpoints

### Adding Tests

Add new tests in `tests/test_api.py`:

```python
@pytest.mark.market_data
def test_new_endpoint(self, session, base_url):
    """Test new endpoint."""
    response = session.get(f"{base_url}/new/endpoint")
    assert response.status_code == 200
```
