"""
@author Kamdin Bembry
"""

import json
import numpy as np
import AlpacaAPI
from AlpacaAPI import AlpacaAPI
from AlpacaAPI import *
import asyncio
import websockets
import pandas as pd
import threading
import DataStream
from DataStream import Datastream
from DataStream import *
from config import ALPACA_API_KEY
from config import ALPACA_SECRET_KEY
import logging
    
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TradingBot")
logger.setLevel(logging.DEBUG)

class TradingBot:
    def __init__(self, alpaca_api, datastream_uri):
        """
        Initialize TradingBot with Alpaca API keys and create an Alpaca API instance.
        """
        self.alpaca = alpaca_api
        self.running = True
        self.lock = threading.Lock()
        self.queue = asyncio.Queue()  # Queue for sharing data_update output.
        self.datastream = Datastream(datastream_uri) #datastream instance for websockets


    async def update_live_data(self, symbols):
        """
        Use Datastream to receive live data for the given symbol.
        """
        if not await self.datastream.connect_with_retries(): #retry if necessary
                logger.error("Unable to establish Websocket connection")
                return
        
        try:
            # Authenticate w/ Alpaca API websocket
            auth_data = {
                "action": "authenticate",
                "key": ALPACA_API_KEY,
                "secret": ALPACA_SECRET_KEY,
            }
            await self.datastream.send_data(json.dumps(auth_data))  
            response = await self.datastream.receive_data() 
            logger.info(f"Auth response: {response}")

            # Subscribe to market data for multiple symbols in one connection
            request_data = {
                "action": "subscribe",
                "bars": symbols,
            }
            await self.datastream.send_data(json.dumps(request_data))
            logger.info(f"Subscribed to {symbols}")
            
            while self.running:
                try:
                    data = await self.datastream.receive_data()
                    if data:  # Only process non-None data
                        await self.queue.put(json.loads(data))
                except Exception as e:
                    logger.error(f"Error while retrieving data: {e}")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid json received: {e}")
        finally:
            await self.datastream.close()

                        
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

            

    # def evaluate_market_conditions(self, data, symbol):     # lets turn this into a nubmer from 1 to 10, and if it is above 8, it will be considered a highly volatile stock and should be dealt with differently
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
          

    async def monitor_market(self):
        """
        A method to monitor market conditions for all symbols.
        """  
        while self.running:
            try:
                data = await self.queue.get()
                df = pd.DataFrame(data)
                for symbol in df['symbol'].unique():  # Iterate over all symbols
                    symbol_data = df[df['symbol'] == symbol]
                    symbol_data['ShortAvg'] = symbol_data['c'].rolling(20).mean()
                    symbol_data['LongAvg'] = symbol_data['c'].rolling(50).mean()
                    signals = self.moving_average_crossover(symbol_data[['ShortAvg', 'LongAvg']])
                    if signals[-1] != 0:
                        self.execute_trades(signals[-1], symbol)
                    else:
                        logger.info(f"Holding position for {symbol}.")
                await asyncio.sleep(60)  # Sleep before processing new data
            except Exception as e:
                logger.error(f"Error monitoring market: {e}")



    async def forward_to_local_server(self):
        """
        Forward data to the local WebSocket server at ws://localhost:8080.
        """
        local_uri = "ws://localhost:8080"
        local_stream = Datastream(local_uri)
        try:
            if not await local_stream.connect_with_retries():
                logger.error("Unable to connect to the local WebSocket server.")
                return
            
            while self.running:
                try:
                    # Fetch data from the bot's queue
                    data = await self.queue.get()
                    
                    # Send data to the server
                    await local_stream.send_data(json.dumps(data))
                    logger.info(f"Data forwarded to local server: {data}")
                    
                    # Await server's response (optional)
                    response = await local_stream.receive_data()
                    logger.info(f"Response from server: {response}")
                except Exception as e:
                    await asyncio.sleep(.5)
                    logger.error(f"Error forwarding data: {e}")
        except Exception as e:
            logger.error(f"Error connecting to local server: {e}")
        finally:        
            await local_stream.close()



    async def run(self):
        """
        Starts the bot for all positions.
        """
        positions = self.alpaca.fetch_positions()
        symbols = list(positions.keys())
        tasks = [
            self.safe_task(self.update_live_data,symbols),    
            self.safe_task(self.monitor_market),
            self.safe_task(self.forward_to_local_server)
            ]
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

    alpaca = AlpacaAPI(ALPACA_API_KEY, ALPACA_SECRET_KEY)
    datastream_uri = "wss://paper-api.alpaca.markets/stream"
    bot = TradingBot(alpaca, datastream_uri)
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