
class Posman:
    def __init__(self, bot) -> None:
        self.bot = bot

    def calculate_position_value(self, symbol):
        """
        Calculate the value of a position (quantity * price).
        """
        qty = self.bot.alpaca.positions.get(symbol)[0]
        price = self.bot.alpaca.positions.get(symbol)[1]
        return qty * price 
    
    def available_funds(self):
        """
        returns uninvested funds
        """
        cash = self.bot.alpaca.calculate_portfolio_value()
        positions = self.bot.alpaca.fetch_positions()
        for symbol in positions:
            cash -= self.calculate_position_value(symbol=symbol)
        return cash
    
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
        print(f"Stop-loss set to {stop_loss_price}")
        return stop_loss_price