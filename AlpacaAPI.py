import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import TimeFrame, REST
from datetime import date, timedelta
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AlpacaAPI")#="TradingBot"
logger.setLevel(logging.INFO)


class AlpacaAPI:
    def __init__(self, api_key, secret_key, base_url="https://paper-api.alpaca.markets"):
        """
        Alpaca API wrapper for trading and data fetching using alpaca-trade-api.
        """
        self.api = tradeapi.REST(api_key, secret_key, base_url)
        self.positions = {}
        self.checkbook = {}  # Track buy prices for symbols # <--- To be Implemented

    def populate_checkbook(self):
        """
        Fetch past buy orders and populate the checkbook with the buy price.
        """
        try:
            # Fetch all closed orders (or you can adjust with time range/limit)
            orders = self.api.list_orders(status='filled', limit=500)  # Adjust 'limit' as needed

            for order in orders:
                # Only process buy orders
                if order.side == 'buy' and order.filled_avg_price:
                    symbol = order.symbol
                    buy_price = float(order.filled_avg_price)

                    # Add to checkbook if not already added
                    if symbol not in self.checkbook:
                        self.checkbook[symbol] = buy_price
                        logging.info(f"Added {symbol} to checkbook with buy price {buy_price}")

        except Exception as e:
            logging.error(f"Error populating checkbook: {e}")

    def fetch_positions(self):
        """
        Fetch current positions from Alpaca API.
        """
        try:
            positions = self.api.list_positions()
            self.positions = {pos.symbol: [int(pos.qty), float(pos.current_price)] for pos in positions}
            return self.positions
        
        except tradeapi.rest.APIError as e:
            raise Exception(f"Error fetching positions: {e}")


    def place_order(self, symbol, qty, side="buy", order_type="market", time_in_force="gtc"):
        """
        Place an order via Alpaca API.
        """
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force,
            )
            print(f"Order placed: {order}")
        except tradeapi.rest.APIError as e:
            raise Exception(f"Error placing order: {e}")

    def calculate_portfolio_value(self):
        """
        Calculate the total portfolio value.
        """
        try:
            account = self.api.get_account()
            return float(account.portfolio_value)
        except tradeapi.rest.APIError as e:
            raise Exception(f"Error fetching portfolio value: {e}")

    def fetch_historical_data(self, symbol, start_date):
        try:
            end_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
            bars = self.api.get_bars(
                symbol,
                TimeFrame.Day,
                start=start_date,
                end=end_date,
                adjustment='all'
            ).df
            #logging.info(f"Data retrieved: {bars.tail(3)}")
            return bars
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            raise
    
    def fetch_raw_data(self, symbol):
        """
        Fetches all of the current data
        """
        return self.api.get_latest_bar(symbol=symbol, feed='iex')

    def is_market_open(self):
        """
        Check if the market is currently open.
        """
        try:
            clock = self.api.get_clock()
            return clock.is_open
        except tradeapi.rest.APIError as e:
            raise Exception(f"Error checking market status: {e}")

    def get_account_info(self):
        """
        Retrieve account details.
        """
        try:
            return self.api.get_account()
        except tradeapi.rest.APIError as e:
            raise Exception(f"Error fetching account information: {e}")


# Example usage
if __name__ == "__main__":
    from config import ALPACA_API_KEY, ALPACA_SECRET_KEY

    alpaca = AlpacaAPI(ALPACA_API_KEY, ALPACA_SECRET_KEY)

    # # Fetch positions
    # positions = alpaca.fetch_positions()
    # print("Positions:", positions)

    # # Place an order
    # try:
    #     alpaca.place_order("RGTI", 1, side="buy")
    # except Exception as e:
    #     print(f"Error placing order: {e}")

    # Fetch historical data
    data = alpaca.fetch_historical_data("RGTI", "2024-11-01")
    print(data)
    print("\n\n")
    raw_data = alpaca.api.get_latest_bars("RGTI")
    print(raw_data)

    # # Check if market is open
    # is_open = alpaca.is_market_open()
    # print("\nMarket is open:", is_open)
    # print("\n", alpaca.calculate_portfolio_value())
