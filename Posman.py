import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Posman")
logger.setLevel(logging.INFO)

class Posman:
    def __init__(self, bot) -> None:
        self.bot = bot

    def calculate_position_value(self, symbol):
        """
        Calculate the total value of all stocks for a given symbol based on quantity and buy price.
        """
        try:
            # Ensure the symbol exists in both positions and the checkbook
            if symbol not in self.bot.alpaca.positions:
                raise ValueError(f"Symbol {symbol} not found in positions.")
            
            if symbol not in self.bot.alpaca.checkbook:
                raise ValueError(f"Buy price for {symbol} not found in checkbook.")
            
            # Get the quantity of stocks held for the symbol
            qty = self.bot.alpaca.positions[symbol]['qty']
            if not qty or qty <= 0:
                raise ValueError(f"Invalid quantity {qty} for symbol {symbol}.")
            
            # Get the average buy price from the checkbook
            buy_prices = self.bot.alpaca.checkbook[symbol]
            if not isinstance(buy_prices, list) or not buy_prices:
                raise ValueError(f"No buy prices recorded for symbol {symbol}.")
            
            avg_buy_price = sum(buy_prices) / len(buy_prices)

            # Calculate the total position value
            total_position_value = avg_buy_price * qty
            return total_position_value

        except Exception as e:
            logging.error(f"Error calculating position value for {symbol}: {e}")
            raise

    
    def available_funds(self):
        """
        returns uninvested funds
        """
        try:
            total_portfolio_value = self.bot.alpaca.calculate_portfolio_value()
            total_positions_value = 0
            positions = self.bot.alpaca.fetch_positions()

            for symbol in positions:
                total_positions_value += self.calculate_position_value(symbol=symbol)
            available_funds = float(total_portfolio_value) - total_positions_value
            return available_funds
        except Exception as e:
            print("Error calculating funds...")
            return 0.0

    
    def position_sizing_strategy(self, symbol, portfolio_value, available_cash, max_position_size=0.10):
        """
        Ensures no single position exceeds a defined percentage of the portfolio.
        """
        position_value = self.calculate_position_value(symbol)
        max_allocation = portfolio_value * max_position_size

        if position_value > max_allocation or available_cash < position_value:
            return -1  # Don't add to position
        return 0  # Neutral
    
    def calculate_stop_loss(self, entry_price, risk_threshold=0.05):
        """
        Calculate stop-loss price based on entry price and risk threshold.
        """
        stop_loss_price = entry_price * (1 - risk_threshold)
        #print(f"Stop-loss set to {stop_loss_price}")
        return stop_loss_price