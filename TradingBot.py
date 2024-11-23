import json
import AlpacaAPI
import numpy as np
from AlpacaAPI import AlpacaAPI
from AlpacaAPI import *
import asyncio
import websockets
import pandas as pd
import threading
from datetime import datetime, timedelta
from config import ALPACA_API_KEY
from config import ALPACA_SECRET_KEY
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TradingBot")

class TradingBot:
    def __init__(self, alpaca_api):
        """
        Initialize TradingBot with Alpaca API keys and create an Alpaca API instance.
        """
        self.alpaca = alpaca_api
        self.running = True
        self.lock = threading.Lock()
        self.queue = asyncio.Queue()  # Queue for sharing data_update output.


    async def update_live_data(self, symbol):
        url = "wss://paper-api.alpaca.markets/stream"
        async with websockets.connect(url) as websocket:
            try:
                auth_data = {
                    "action": "authenticate",
                    "key": ALPACA_API_KEY,
                    "secret": ALPACA_SECRET_KEY,
                }
                await websocket.send(json.dumps(auth_data))
                response = await websocket.recv()
                logger.info(f"Auth response: {response}")

                # Subscribe to market data for multiple symbols in one connection
                request_data = {
                    "action": "subscribe",
                    "bars": [symbol],
                }
                await websocket.send(json.dumps(request_data))
                logger.info(f"Subscribed to {symbol}")
                
                while self.running:
                    try:
                        data = await websocket.recv()
                        await self.queue.put(json.loads(data))
                    except Exception as e:
                        logger.error(f"Error while receiving data: {e}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")

                        


    def moving_average_crossover(self, data):
        """
        Strategy: Generate buy (1) and sell (-1) signals based on moving average crossover.
        """
        signals = []
        for i in range(len(data)):
            if data.iloc[i, 0] > data.iloc[i, 1]:
                signals.append(1)  # BUY signal
            elif data.iloc[i, 0] < data.iloc[i, 1]:
                signals.append(-1)  # SELL signal
            else:
                signals.append(0)  # No signal
        return np.array(signals)


    def backtest_strategy(self, data):
        """
        Backtests the moving average crossover strategy.
        Returns cumulative returns of the strategy.
        """
        """ 
        This provides the actual daily return for the asset.
            * signals: Multiplies the daily return by the corresponding signal to apply the trading strategy:
            A signal of 1 means you profit (or lose) based on the price movement.
            A signal of -1 means you gain if the price falls (short-selling).
            A signal of 0 means no position is taken, so the return is 0.
            .cumsum(): Computes the cumulative sum of the returns over time, reflecting the overall performance of the strategy.
            """
        signals = self.moving_average_crossover(data)
        returns = (data['c'].pct_change() * signals).cumsum()
        return returns

    
    def execute_trades(self, signal, symbol):
        """
        Execute trades based on the signal. Signal:
        - 1: Buy
        - -1: Sell
        """
        with self.lock:
            self.alpaca.fetch_positions()
            logger.info(f"Processing signal {signal} for {symbol}")

            if signal == 1:  # BUY
                logger.info(f"Placing BUY order for {symbol}")
                self.alpaca.place_order(symbol, qty=1, side="buy")
            elif signal == -1:  # SELL
                logger.info(f"Placing SELL order for {symbol}")
                self.alpaca.place_order(symbol, qty=1, side="sell")
            else:
                logger.info(f"Placing SELL order for {symbol}")

            print(f"Trade for {symbol} completed. Notifying other threads.")
            self.lock.notifyAll() #Notify waiting threads that they can now trade

            

    # def evaluate_market_conditions(self, data, symbol):
    #     """
    #     Analyze market trends and make action decisions.
    #     """
    #     short_avg = data['c'].rolling(20).mean().iloc[-1]
    #     long_avg = data['c'].rolling(50).mean().iloc[-1]
    #     current_price = data['c'].iloc[-1]
    #     atr = self.calculate_volatility(data) #incorporate this volatility in the future.

    #     stop_loss_price = self.calculate_stop_loss(entry_price=current_price, risk_threshold=0.05)

    #     # Decision logic
    #     if short_avg > long_avg and current_price > stop_loss_price:
    #         return "buy", 1
    #     if current_price < stop_loss_price:
    #         return "sell", self.alpaca.positions[symbol]
    #     elif short_avg < long_avg:
    #         if symbol in self.alpaca.positions and current_price < (self.alpaca.positions[symbol] * 0.95):
    #             return "sell", self.alpaca.positions[symbol]
    #     else:
    #         return None, 0
            

    async def monitor_market(self, symbol):
        """
        A method to monitor market conditions for the symbol, potentially watching for changes or thresholds.
        """
        while self.running:
            try:              
                print("in monitor_market()")  
                data = await self.queue.get()
                df = pd.DataFrame(data)
                df['ShortAvg'] = df['c'].rolling(20).mean().fillna(0)
                df['LongAvg'] = df['c'].rolling(50).mean().fillna(0)
                signals = self.moving_average_crossover(df[['ShortAvg', 'LongAvg']])
                if signals[-1] != 0:  # If there's a trade signal
                    self.execute_trades(signals[-1], symbol)
                else:
                    print(f"Holding position for {symbol}.")
                await asyncio.sleep(60)  # Wait before the next update
            except Exception as e:       
                logger.error(f"Error in {function.__name__}: {e}")
                # Debugging info
                print(f"Debug: Stock={symbol}, Additional Data={data}")



    async def forward_to_local_server(self):
        """
        A method to send some data (e.g., updates, logs, or market data) to a local server for further processing or storage.
        """
        url = "ws://localhost:9999"
        async with websockets.connect(url) as websocket:
            while self.running:
                try:
                    print("in forward_t....()")
                    self.queue = asyncio.Queue(maxsize=100) # limit queue size
                    
                    data = await self.queue.get()  # Fetch data from the queue.
                    await websocket.send(data)  # Forward to the local server.
                except Exception as e:
                    print(f"Error forwarding data: {e}")


    async def run(self):
        """
        Starts the bot for all positions.
        """
        positions = self.alpaca.fetch_positions()
        tasks = []
        print(positions)
        for symbol in positions.keys():
            print(symbol)
            # tasks.append(self.update_live_data(symbol))     
            # tasks.append(self.monitor_market(symbol))
            # tasks.append(self.forward_to_local_server())
            tasks.append(self.safe_task(self.update_live_data,symbol))     
            tasks.append(self.safe_task(self.monitor_market, symbol))
            tasks.append(self.safe_task(self.forward_to_local_server))
        print("In run(), pre gather")
        await asyncio.gather(*tasks) # asyncio.gather(*tasks) collects all the tasks in the list and runs them simultaneously using Python's asyncio framework.
        print("In run(), post gather")

    async def safe_task(self, func, *args):
        try:
            await func(*args)
        except Exception as e:
            print(f"Error in {func.__name__}: {e}")
                


    def calculate_volatility(self, data):
        """
        Calculate Average True Range (ATR) to measure volatility.
        """
        high_low = data['h'] - data['l']
        high_close = abs(data['h'] - data['c'].shift(1))
        low_close = abs(data['l'] - data['c'].shift(1))
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(14).mean()
        return atr.iloc[-1] #Latest ATR value 

        
    def calculate_position_value(self, symbol, price):
        """
        Calculate the value of a position (quantity * price).
        """
        qty = self.alpaca.positions.get(symbol, 0)
        return qty * price * 0.98  # Adjust for slippage


    def calculate_stop_loss(self, entry_price, risk_threshold=0.05):
        """
        Calculate stop-loss price based on entry price and risk threshold.
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

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("TradingBot")

    alpaca = AlpacaAPI(ALPACA_API_KEY, ALPACA_SECRET_KEY)
    bot = TradingBot(alpaca)
    asyncio.run(bot.run())

    print("In main(), post run()")

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
        stop_loss_price = bot.calculate_stop_loss(entry_price=(bot.calculate_position_value() // bot.alpaca.positions[1]), risk_threshold=.05) # i need a method to get price of a symbol share of a position

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

    
        # #Execute trades based on signals
        # for i, signal in enumerate(signals):
        #     print(f"\nProcessing signal {i}: {signal}")
        #     bot.execute_trades(signals[:1], symbol, lock)


    # Modularize the backtesting methods
    """