"""Pytest configuration for IBKR MCP Server tests."""
import pytest
import requests


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "gateway: tests for gateway endpoints"
    )
    config.addinivalue_line(
        "markers", "connection: tests for connection endpoints"
    )
    config.addinivalue_line(
        "markers", "account: tests for account endpoints"
    )
    config.addinivalue_line(
        "markers", "market_data: tests for market data endpoints"
    )
    config.addinivalue_line(
        "markers", "contracts: tests for contract endpoints"
    )
    config.addinivalue_line(
        "markers", "scanners: tests for scanner endpoints"
    )


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the API."""
    return "http://localhost:8000"


@pytest.fixture(scope="session")
def session():
    """Create a requests session."""
    return requests.Session()


@pytest.fixture(scope="session")
def test_stocks():
    """List of test stock symbols."""
    return ["AAPL", "MSFT", "GOOGL"]


@pytest.fixture
def api_url(base_url):
    """Full API URL."""
    return base_url


def make_request(session, method, url, **kwargs):
    """Make an HTTP request and return result."""
    kwargs.setdefault("timeout", 30)
    kwargs.setdefault("headers", {})
    kwargs["headers"].setdefault("Accept", "application/json")
    
    response = session.request(method, url, **kwargs)
    return response
