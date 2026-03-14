"""Main IB interface combining all functionality."""

from .market_data import MarketDataClient
from .contracts import ContractClient
from .scanners import ScannerClient
from .positions import PositionClient
from .history import HistoryClient


class IBInterface(
  MarketDataClient,
  ContractClient,
  ScannerClient,
  PositionClient,
  HistoryClient,
):
  """Main IB interface combining all functionality."""
