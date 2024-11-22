import asyncio
from asyncio import tasks
import AlpacaAPI 
#import PolygonAPI
import pandas as pd
import numpy as np
import threading
from config import alpaca_api_key, alpaca_secret_key
import time
from datetime import datetime, timezone, timedelta

import config


class TradingBot:
    def __init__(self, alpaca_key, alpaca_secret):
        self.alpaca = AlpacaAPI.AlpacaAPI(alpaca_key,alpaca_secret)
        self.running = True
        self.lock = threading.Lock()

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

    
    def execute_trades(self, signal, symbol): # eventually should add a check to make sure that we have enough money to do this.
        """
        Execute trades based on the first signal.
        """
        with lock:          #ensure only one thread accesses this block at a time.
            if signal == 1: # BUY
                if self.alpaca.update_positions(symbol, signal):
                    print("Signal is BUY. Placing order...")
                    self.alpaca.place_order(symbol, 1, "buy")
                else:
                    print(f"Insufficient funds or position issue for {symbol}. Trade skipped.")
                
            elif signal == -1: # SELL
                if self.alpaca.update_positions(symbol, signal):
                    print("Signal is SELL. Placing order...")
                    self.alpaca.place_order(symbol, 1, "sell")
                else:
                    print(f"No holdings to sell for {symbol}. Trade skipped.")

            else:
                print(f"No action taken for {symbol}.")

        print(f"Trade for {symbol} completed. Notifying other threads.")

    def evaluate_market_conditions(self, data, symbol):
        """
        Analyze market trends and make action decisions.
        """
        short_avg = data['c'].rolling(20).mean().iloc[-1]
        long_avg = data['c'].rolling(50).mean().iloc[-1]
        current_price = data['c'].iloc[-1]
        atr = self.calculate_volatility(data)

        # Decision logic
        if short_avg > long_avg:
            if symbol not in self.alpaca.positions:
                return "buy", 1
        elif short_avg < long_avg:
            if symbol in self.alpaca.positions and current_price < (self.alpaca.positions[symbol] * 0.95):
                return "sell", self.alpaca.positions[symbol]
        else:
            return None, 0
            


    def monitor_market(self, symbol):
        """
        watches market for a position to see if action should be taken
        """
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                start_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime('%Y-%m-%d')
                data = self.alpaca.fetch_market_data(symbol=symbol, start_date=start_date, end_date=now.strftime('%Y-%m-%d'))
                df = pd.DataFrame(data)

                #Fetch updated postions
                self.alpaca.fetch_positions()
    
                decision, qty = self.evaluate_market_conditions(df, symbol)



                if decision:
                    with self.lock:
                        self.alpaca.place_order(symbol,qty,side=decision)
                else:
                    print(f"Holding position for {symbol, qty, decision}")    
            except Exception as e:
                print(f"Error in monitoring market: {e}")
            time.sleep(60)


    def run(self, symbol): 
        """
        Starts the bot
        """        
        monitor_thread = threading.Thread(target=self.monitor_market, args=(symbol,))# extra ',' to make it a tuple
        monitor_thread.start()
        return monitor_thread

    def calculate_volatility(self, data):
        """
        Calculate volatility using ATR(Average True Range) or similar metrics
        """
        high_low = data['h'] - data['l']
        high_close = abs(data['h'] - data['c'].shift(1))
        low_close = abs(data['l'] - data['c'].shift(1))
        true_range = pd.concat([high_low, high_close, low_close]).max(axis=1)
        atr = true_range.rolling(14).mean()
        return atr.iloc[-1] # latest ATR value

        
    def calculate_position_value(quantity, price):
        """
        Calculates the value of the current position based on quantity and price.
        """

        return quantity * price * (.98)# accounting for slippage


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
        self.calculate_volatility(current_avg, previous_avg)
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
        tasks
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
    end_date = "2024-11-19"
    try:
        #tasks = [bot.fetch_market_data(symbol) for symbol in ['AAPL', 'TSLA', 'NFLX', 'SPY', 'NVDA', 'QQQ']] # i will need to modify this so that whenever a new stock of some sort is bought, it will be added to the list
        #await asyncio.gather(*tasks)
        #positions = self.alpaca.fetch_positions()
        data:list = bot.fetch_market_data(symbol, start_date, end_date)
        df = pd.DataFrame(data) #Process data into a DataFrame
        df['ShortAvg'] = df['c'].rolling(20).mean().fillna(0) #Short-term mean close price
        df['LongAvg'] = df['c'].rolling(50).mean().fillna(0)  #Long-term mean close price
        #print(df.head())
        print("\nRaw Data:", data)
    except Exception as e:
        print(f"Error fetching market data: {e}")

    signals = bot.moving_average_crossover(df[['ShortAvg', 'LongAvg']])
    returns = bot.backtest_strategy(df[['ShortAvg','LongAvg']])
    stop_loss_price = bot.calculate_stop_loss(entry_price=(bot.calculate_position_value // bot.alpaca.positions[1]), risk_threshold=.05)

    print("\nGenerate Signals: ", signals)
    print("Backtest returns:", returns)
    print(f"Stop loss price: {stop_loss_price}")

    threads = []
    for _ in range(5):
        thread = threading.Thread(target=bot.monitor_market_conditions, args=(df, symbol, lock))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()


    #instead of directly executing trades I want to check on market conditions and then have it make an educated decision based on market data used in stop_loss, position vlaue, and the others, like volatility. it also has to incorporate the lock that i created so only one can execute at a time, the rest will wait, be notified(interrupted), made to wait again, until all have gone.
   
    # #Execute trades based on signals
    # for i, signal in enumerate(signals):
    #     print(f"\nProcessing signal {i}: {signal}")
    #     bot.execute_trades(signals[:1], symbol, lock)
