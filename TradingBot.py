import pandas as pd
from AlpacaAPI import *
import AlpacaAPI
from PolygonAPI import *
import PolygonAPI
import numpy as np
import PolygonAPI
import AlpacaAPI
import os


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
        returns = np.cumprod(1 + signals * .001) -1

        return returns

    def fetch_market_data(self, symbol, start_date, end_date):
        """
        Fetch historical market data from Polygon.io.
        """
        return self.polygon.get_historical_data(symbol, start_date, end_date)

    def execute_trades(self, signals, symbol):
        """
        Execute trades based on the first signal.
        """
        if signals[0] == 1:
            print("Signal is BUY. Placing order...")
            self.alpaca.place_order(symbol, 1, "buy")
        elif signals[0] == -1:
            print("Signal is SELL. Placing order...")
            self.alpaca.place_order(symbol, 1, "sell")
        else:
            print("No action needed.")

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

    def calculate_position_value(position, price):
        """
        Calculates the value of the current position based on quantity and price.
        """
        return position * price


    def calculate_stop_loss(self, entry_price, risk_threshold):
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
        current_avg = data.iloc[-short_window:].mean() #last 20 rows...
        previous_avg = data.iloc[-long_window:].mean() 
        self.monitor_volatility(current_avg, previous_avg)
        return current_avg, previous_avg
    

if __name__ == "__main__":

    #replace with my keys
    polygon_api_key = "zuSAi5YpaO5tghum5I_mjAENN6g8GJrY"
    alpaca_api_key = "PK3Q7DU6TGI2XYLFE3G0"
    alpaca_secret_key = "ucmht0LDjmPRslVXt61AQpNcA58nnPsI9SFtO8VO"

    #initialize bot
    bot = TradingBot(polygon_api_key, alpaca_api_key, alpaca_secret_key)

    #Fetch historical data
    symbol = "AAPL"
    start_date = "2023-01-01"
    end_date = "2024-11-14"
    try:
        data = bot.fetch_market_data(symbol, start_date, end_date)
        print("Raw Data:", data)
    except Exception as e:
        print(f"Error fetching market data: {e}")

    #Process data into a DataFrame
    df = pd.DataFrame(data=data)
    df['ShortAvg'] = df['c'].rolling(20).mean() #Short-term mean close price
    df['LongAvg'] = df['c'].rolling(50).mean()  #Long-term mean close price

    signals = bot.moving_average_crossover(df[['ShortAvg', 'LongAvg']])
    print("Generate Signals: ", signals)

    # returns = bot.backtest_strategy(df[['ShortAvg','LongAvg']])
    # print("Backtest returns:", returns)

    #Execute trades based on signals
    for i, signal in enumerate(signals):
        print(f"Processing signal {i}: {signal}")
        bot.execute_trades([signals], symbol)

    try:
        bot.alpaca.place_order("AAPL", 1, "buy")
    except Exception as e:
        print(f"Error placing order: {e}")

