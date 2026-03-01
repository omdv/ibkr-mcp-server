# Testing Instructions for IBKR MCP Server

## Running the Server

Start the server using the provided script:

```bash
./run.sh
```

This will:
1. Install dependencies using `uv sync --reinstall`
2. Start the IBKR MCP Server on port 8000
3. Automatically start the IBKR Gateway Docker container

## Testing with curl

### Check Server Status

```bash
# Server root - should return welcome message
curl http://localhost:8000/

# Gateway status
curl http://localhost:8000/gateway/status

# Gateway container logs
curl http://localhost:8000/gateway/logs?tail=50
```

### IBKR Connection Endpoints

```bash
# Connection status
curl http://localhost:8000/ibkr/connection/status

# Reconnect if needed
curl -X POST http://localhost:8000/ibkr/connection/reconnect
```

### Account Endpoints

```bash
# Account summary
curl http://localhost:8000/ibkr/account/summary

# Positions
curl http://localhost:8000/ibkr/account/positions
```

### Market Data Endpoints

```bash
# Market data snapshot
curl "http://localhost:8000/ibkr/market_data/snapshot?symbol=AAPL&sec_type=STK"

# Historical data
curl "http://localhost:8000/ibkr/market_data/historical?symbol=AAPL&duration=1%20D&bar_size=1%20min"

# Tickers
curl "http://localhost:8000/ibkr/tickers?symbol=AAPL"
```

### Contract Endpoints

```bash
# Contract details
curl "http://localhost:8000/ibkr/contract_details?symbol=AAPL&sec_type=STK&exchange=SMART&currency=USD"

# Options chain
curl "http://localhost:8000/ibkr/options_chain?underlying_symbol=AAPL&underlying_con_id=265598&exchange=SMART"
```

### Scanner Endpoints

```bash
# Scanner results
curl "http://localhost:8000/ibkr/scanner/results?instrument=STK&location_code=STK.US.MAJOR"
```

## Viewing Logs

### Application Logs

Application logs are written to `logs/app.log` when file logging is enabled.

```bash
# View all logs
cat logs/app.log

# Watch logs in real-time
tail -f logs/app.log

# View last 50 lines
tail -n 50 logs/app.log
```

### Enable File Logging

Add to your `.env` file:

```bash
ENABLE_FILE_LOGGING=true
LOG_FILE_PATH=logs/app.log
LOG_LEVEL=INFO
```

### Gateway Container Logs

```bash
# Via API
curl http://localhost:8000/gateway/logs?tail=100

# Or directly via Docker
docker logs ibkr-gateway
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- MCP Server: http://localhost:8000/mcp

## Troubleshooting

### Server Not Starting

1. Check if Docker is running: `docker ps`
2. Check if port 8000 is available: `lsof -i :8000`
3. Verify credentials in `.env` file

### Connection Issues

1. Check Gateway status: `curl http://localhost:8000/gateway/status`
2. Check connection status: `curl http://localhost:8000/ibkr/connection/status`
3. Review application logs: `tail -f logs/app.log`

### View Docker Container

Access IBKR Gateway VNC at: http://localhost:6080/
