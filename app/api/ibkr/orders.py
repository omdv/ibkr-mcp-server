"""Orders-related tools."""
from fastapi.responses import JSONResponse
from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger

@ibkr_router.get("/limit_order", operation_id="create_limit_order")
async def create_limit_order(
  action: str,
  quantity: int,
  price: float,
) -> dict:
  """Create a limit order.

  Args:
    action: Action to take on the order, must be either BUY or SELL.
    quantity: Quantity to order.
    price: Price to order at.

  Returns:
    dict: A dictionary containing the order

  Example:
    >>> create_limit_order(action="BUY", quantity=100, price=150.25)
    {"contract":"AAPL","position":100,"avgCost":150.25,"contractId":123456}

  """
  try:
    logger.debug("Creating limit order")
    order = await ib_interface.create_limit_order(action, quantity, price)
  except Exception as e:
    logger.error("Error in create_limit_order: {!s}", str(e))
    return JSONResponse(content=[], media_type="application/json")
  else:
    logger.debug("Order: {order}", order=order)
    return JSONResponse(content=order, media_type="application/json")
