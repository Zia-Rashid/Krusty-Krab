import alpaca_trade_api as tradeapi
from datetime import date


class AlpacaAPI:
    def __init__(self, api_key, secret_key, base_url="https://paper-api.alpaca.markets"):
        """
        Alpaca API wrapper for trading and data fetching using alpaca-trade-api.
        """
        self.api = tradeapi.REST(api_key, secret_key, base_url)
        self.positions = {}

    def fetch_positions(self):
        """
        Fetch current positions from Alpaca API.
        """
        try:
            positions = self.api.list_positions()
            #print(positions)
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

    def fetch_historical_data(self, symbol, start_date, timeframe="1D"):
        """
        Fetch historical market data.
        """
        parts = str(date.today()).split("-")
        part = int(parts[2]) - 1
        yesterday = f"{parts[0]}-{parts[1]}-{part}"
        
        try:
            bars = self.api.get_bars(symbol, timeframe, start=start_date, end=yesterday).df
            return bars
        except tradeapi.rest.APIError as e:
            raise Exception(f"Error fetching historical data: {e}")

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

    # Fetch positions
    positions = alpaca.fetch_positions()
    print("Positions:", positions)

    # # Place an order
    # try:
    #     alpaca.place_order("AAPL", 1, side="buy")
    # except Exception as e:
    #     print(e)

    # # Fetch historical data
    # data = alpaca.fetch_historical_data("NFLX", "2024-11-01")
    # print(data)

    # # Check if market is open
    # is_open = alpaca.is_market_open()
    # print("Market is open:", is_open)
    # print("\n\n")
    print(alpaca.calculate_portfolio_value())
