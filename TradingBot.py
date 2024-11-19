import pandas as pd
#from AlpacaAPI import *
import AlpacaAPI
#from PolygonAPI import 
import PolygonAPI
import numpy as np
import threading
import os
import config



class TradingBot:
    def __init__(self, polygon_key, alpaca_key, alpaca_secret):
        self.polygon = PolygonAPI.PolygonAPI(polygon_key)#still not entirely sure why i need the polygon twice.
        self.alpaca = AlpacaAPI.AlpacaAPI(alpaca_key,alpaca_secret)

    def moving_average_crossover(self, data):
        """
        Strat: Generates buy(1) and sell(-1) signals based on moving avg crossover
        """
        signals = []
        for i in range(len(data)):
            if data.iloc[i, 0] > data.iloc[i, 1]:  # Short-term average > Long-term average
                signals.append(1)  # BUY signal
            elif data.iloc[i, 0] < data.iloc[i, 1]:  # Short-term average < Long-term average
                signals.append(-1)  # SELL signal
            else:
                signals.append(0)  # No signal
        
        return np.array(signals)  # Return as NumPy array for easier processing

    def backtest_strategy(self, data):
        """
        Backtests the moving average crossover strategy.
        """
        signals = self.moving_average_crossover(data)
        returns = (data['c'].pct_change() * signals).cumsum()
        """This provides the actual daily return for the asset.
            * signals: Multiplies the daily return by the corresponding signal to apply the trading strategy:
            A signal of 1 means you profit (or lose) based on the price movement.
            A signal of -1 means you gain if the price falls (short-selling).
            A signal of 0 means no position is taken, so the return is 0.
            .cumsum(): Computes the cumulative sum of the returns over time, reflecting the overall performance of the strategy."""

        return returns

    def fetch_market_data(self, symbol, start_date, end_date):
        """
        Fetch historical market data from Polygon.io.
        """
        return self.polygon.get_historical_data(symbol, start_date, end_date)

    def execute_trades(self, signal, symbol):
        """
        Execute trades based on the first signal.
        """
        #open_orders = self.alpaca.get_open_orders(symbol)
        #if open_orders:
        #   print(f"Opend orders found for {symbol}: {open_orders})
        #   return
        if signal == 1: #if they want to buy
            #eventually should add a check to make sure that we have enough money to do this.
            print("Signal is BUY. Placing order...")
            self.alpaca.place_order(symbol, 1, "buy")
            self.alpaca.update_positions() 
            
        elif signal == -1: #if they want to sell:
            if self.alpaca.update_positions():
                print("Signal is SELL. Placing order...")
                self.alpaca.place_order(symbol, 1, "sell")
            else:
                print("We cannot sell something that we don't have.")

        else:
            print("No action taken.")

    def monitor_volatility(self, current_avg, previous_avg):
        """
        Monitors volatility and identifies potential trend reversals.
        """
        if current_avg > previous_avg:
            print("Trend is strong. Holding.")
            return
        
        # Set threshold for drop percentage
        threshold = 5  # 5%

        # Calculate drop percentage
        drop_percentage = (previous_avg - current_avg) / previous_avg * 100

        # Check if the drop exceeds the threshold
        if drop_percentage >= threshold:
            print("Trend has reversed. Sending SELL request...")
            self.alpaca.place_order("SELL", 1, "sell")
        else:
            print(f"Trend is stabilizing. Drop percentage: {drop_percentage:.2f}%")

    def calculate_position_value(quantity, price):
        """
        Calculates the value of the current position based on quantity and price.
        """
        return quantity * price


    def calculate_stop_loss(self, entry_price, risk_threshold): # find out how to incorporate this.
        """
        Sets a stop-loss price based on entry price and risk threshold.
        """
        stop_loss_price = entry_price * (1 - risk_threshold)
        print(f"Stop-loss set to {stop_loss_price}")
        return stop_loss_price
    
    def update_averages(self, data, short_window=20, long_window=50):
        """
        Updates moving averages and monitors for trend reversals or high volatility.
        """
        current_avg = data.iloc[-short_window:].mean().iloc[-1] #last 20 rows...
        previous_avg = data.iloc[-long_window:].mean() 
        self.monitor_volatility(current_avg, previous_avg)
        return current_avg, previous_avg
    

if __name__ == "__main__":

    """
    symbol = "AAPL"
    start_date = "2023-01-01"
    end_date = "2024-11-14"

    bot = TradingBot(
        os.getenv("POLYGON_API_KEY"),
        os.getenv("ALPACA_API_KEY"),
        os.getenv("ALPACA_SECRET_KEY"),
    )

    try:
        raw_data = bot.fetch_market_data(symbol, start_date, end_date)
        df = pd.DataFrame(raw_data)
        df['ShortAvg'] = df['c'].rolling(20).mean().fillna(0)
        df['LongAvg'] = df['c'].rolling(50).mean().fillna(0)

        signals = bot.moving_average_crossover(df[['ShortAvg', 'LongAvg']])
        bot.execute_trades(signals[:1], symbol)
    except Exception as e:
        print(f"Error: {e}")
"""

    #initialize bot
    bot = bot = TradingBot(config.polygon_api_key, config.alpaca_api_key, config.alpaca_secret_key)
    
    #initialize lock
    lock = threading.Lock()                     #make it so one order can be executed at a time.

    #Fetch historical data
    symbol = "NFLX"
    start_date = "2023-01-01"
    end_date = "2024-11-14"
    try:
        data:list = bot.fetch_market_data(symbol, start_date, end_date)
        print("\nRaw Data:", data)
    except Exception as e:
        print(f"Error fetching market data: {e}")

    

    #Process data into a DataFrame
    df = pd.DataFrame(data)
    df['ShortAvg'] = df['c'].rolling(20).mean().fillna(0) #Short-term mean close price
    df['LongAvg'] = df['c'].rolling(50).mean().fillna(0)  #Long-term mean close price
    print(df.head())
   
    signals = bot.moving_average_crossover(df[['ShortAvg', 'LongAvg']])
    returns = bot.backtest_strategy(df[['ShortAvg','LongAvg']])
    stop_loss_price = bot.calculate_stop_loss(entry_price=860, risk_threshold=.05)

    print("\nGenerate Signals: ", signals)
    print("Backtest returns:", returns)
    print(f"Stop loss price: {stop_loss_price}")

    #instead of directly executing trades I want to check on market conditions and then have it make an educated decision based on market data used in stop_loss, position vlaue, and the others, like volatility. it also has to incorporate the lock that i created so only one can execute at a time, the rest will wait, be notified(interrupted), made to wait again, until all have gone.
   
    # #Execute trades based on signals
    # for i, signal in enumerate(signals):
    #     print(f"\nProcessing signal {i}: {signal}")
    #     bot.execute_trades(signals[:1], symbol, lock)
