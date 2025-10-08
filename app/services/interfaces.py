"""Main IB interface combining all functionality."""
from .market_data import MarketDataClient
from .contracts import ContractClient
from .scanners import ScannerClient
from .positions import PositionClient
from .orders import OrdersClient

class IBInterface(
  MarketDataClient,
  ContractClient,
  ScannerClient,
  PositionClient,
  OrdersClient,
):
  """Main IB interface combining all functionality."""
