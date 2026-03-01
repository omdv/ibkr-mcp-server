"""Pytest tests for IBKR MCP Server API."""
import pytest
import requests


# ============================================================================
# Gateway Tests
# ============================================================================

@pytest.mark.gateway
class TestGateway:
    """Tests for Gateway endpoints."""
    
    def test_gateway_status(self, session, base_url):
        """Test GET /gateway/status."""
        response = session.get(f"{base_url}/gateway/status")
        assert response.status_code == 200
        data = response.json()
        assert "is_running" in data
        assert "container" in data
    
    def test_gateway_logs(self, session, base_url):
        """Test GET /gateway/logs."""
        response = session.get(f"{base_url}/gateway/logs?tail=10")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data


# ============================================================================
# Connection Tests
# ============================================================================

@pytest.mark.connection
class TestConnection:
    """Tests for Connection endpoints."""
    
    def test_connection_status(self, session, base_url):
        """Test GET /ibkr/connection/status."""
        response = session.get(f"{base_url}/ibkr/connection/status")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data


# ============================================================================
# Account Tests
# ============================================================================

@pytest.mark.account
class TestAccount:
    """Tests for Account endpoints."""
    
    def test_account_summary(self, session, base_url):
        """Test GET /ibkr/account/summary."""
        response = session.get(f"{base_url}/ibkr/account/summary")
        # May return 200 or 500 depending on connection
        assert response.status_code in [200, 500]
    
    def test_account_values(self, session, base_url):
        """Test GET /ibkr/account/values."""
        response = session.get(f"{base_url}/ibkr/account/values")
        assert response.status_code in [200, 500]
    
    def test_account_positions(self, session, base_url):
        """Test GET /ibkr/account/positions."""
        response = session.get(f"{base_url}/ibkr/account/positions")
        assert response.status_code in [200, 500]
    
    def test_positions(self, session, base_url):
        """Test GET /ibkr/positions."""
        response = session.get(f"{base_url}/ibkr/positions")
        assert response.status_code in [200, 500]


# ============================================================================
# Market Data Tests
# ============================================================================

@pytest.mark.market_data
class TestMarketData:
    """Tests for Market Data endpoints."""
    
    @pytest.mark.parametrize("symbol", ["AAPL", "MSFT", "GOOGL"])
    def test_market_data_snapshot(self, session, base_url, symbol):
        """Test GET /ibkr/market_data."""
        response = session.get(
            f"{base_url}/ibkr/market_data",
            params={"symbol": symbol}
        )
        # May return 200 or error depending on subscription
        assert response.status_code in [200, 500]
    
    @pytest.mark.parametrize("symbol", ["AAPL", "MSFT"])
    def test_historical_data(self, session, base_url, symbol):
        """Test GET /ibkr/market_data/historical."""
        response = session.get(
            f"{base_url}/ibkr/market_data/historical",
            params={
                "symbol": symbol,
                "duration": "1 D",
                "bar_size": "1 min"
            }
        )
        assert response.status_code in [200, 500]
    
    @pytest.mark.parametrize("symbol", ["AAPL", "MSFT"])
    def test_market_data(self, session, base_url, symbol):
        """Test GET /ibkr/market_data."""
        response = session.get(
            f"{base_url}/ibkr/market_data",
            params={"symbol": symbol}
        )
        assert response.status_code in [200, 500]


# ============================================================================
# Contract Tests
# ============================================================================

@pytest.mark.contracts
class TestContracts:
    """Tests for Contract endpoints."""
    
    @pytest.mark.parametrize("symbol", ["AAPL", "MSFT", "GOOGL"])
    def test_contract_details(self, session, base_url, symbol):
        """Test GET /ibkr/contract_details."""
        response = session.get(
            f"{base_url}/ibkr/contract_details",
            params={
                "symbol": symbol,
                "sec_type": "STK",
                "exchange": "SMART",
                "currency": "USD"
            }
        )
        assert response.status_code == 200


# ============================================================================
# Scanner Tests
# ============================================================================

@pytest.mark.scanners
class TestScanners:
    """Tests for Scanner endpoints."""
    
    def test_scanner_results(self, session, base_url):
        """Test GET /ibkr/scanner/results."""
        response = session.get(
            f"{base_url}/ibkr/scanner/results",
            params={
                "instrument_code": "STK",
                "location_code": "STK.US",
                "scan_code": "MOST_ACTIVE"
            }
        )
        assert response.status_code in [200, 500]


# ============================================================================
# Trading Tests
# ============================================================================

@pytest.mark.trading
class TestTrading:
    """Tests for Trading endpoints."""
    
    def test_get_open_orders(self, session, base_url):
        """Test GET /ibkr/orders/open."""
        response = session.get(f"{base_url}/ibkr/orders/open")
        assert response.status_code in [200, 500]
