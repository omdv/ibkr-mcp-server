"""Orders operations."""
from ib_async.order import LimitOrder, Order

from app.core.setup_logging import logger
from .client import IBClient

class OrdersClient(IBClient):
  """Orders operations."""

  async def create_limit_order(
    self,
    action: str,
    quantity: int,
    price: float,
  ) -> Order:
    """Create a limit order.

    Args:
      contract: Contract to create the order for.
      action: Action to take on the order.
      quantity: Quantity to order.
      price: Price to order at.

    Returns:
      List of orders.

    """
    action = action.upper()

    if action not in ["BUY", "SELL"]:
      logger.error("Action must be either BUY or SELL")
      return None

    try:
      await self._connect()
      order = LimitOrder(action, quantity, price)
      logger.debug("Order: {}", order)
    except Exception as e:
      logger.error("Error getting limit order: {}", str(e))
      raise
    else:
      return order
