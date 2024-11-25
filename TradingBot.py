import signal
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
import alpaca_trade_api as trade_api
    
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
        self.queue = asyncio.Queue(maxsize=1000)  # Queue for sharing data_update output.
        self.datastream = Datastream(datastream_uri) #datastream instance for websockets
        self.buy_prices = {}  # Track buy prices for symbols # <--- To be Implemented

    def is_market_open(self):
        try:
            api = trade_api.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://paper-api.alpaca.markets")
            clock = api.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False



    async def update_live_data(self, symbols:list):
        """
        Use Datastream to receive live data for the given symbol.
        """
        if not await self.datastream.connect_with_retries(): #retry if necessary
                logger.error("Unable to establish Websocket connection")
                for symbol in symbols:
                    self.fetch_historical_data(symbol, "2023-01-01", "2024-11-22")
                return

        if not self.is_market_open():
            logger.info("Market is closed. Skipping love data updates...")
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
                    data = await asyncio.wait_for(self.datastream.receive_data(),timeout=10)
                    if data:  # Only process non-None data
                        logger.debug(f"Raw data received: {e}")
                        if self.queue.full():
                            await self.queue.get_nowait()   # removes oldest item
                        await self.queue.put_nowait(json.loads(data))  # adds new item
                except asyncio.TimeoutError:
                    logger.warning("Websocket recevied time out")
                except Exception as e:
                    logger.error(f"Error while retreiving data: {e}")
        finally:
                await self.datastream.close()
            
    
    async def purge_queue(self):
        while self.running:
            try:
                while not self.queue.empty():
                    await self.queue.get_nowait()  # Clear one item
                await asyncio.sleep(60)  # Run every 60 seconds
            except Exception as e:
                logger.error(f"Error purging queue: {e}")

               
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
    
    def fetch_historical_data(self, symbol, start_date, end_date):
        try:
            api = trade_api.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://paper-api.alpaca.markets")
            bars = api.get_bars(symbol, "1Day", start=start_date, end=end_date)
            logger.info(f"Fetched historical data for {symbol}")
            return bars
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None


    async def mock_data_stream(self, symbols):
        """
        Testing data since it is the weekend
        """
        while self.running:
            try:
                mock_data = {
                    "stream": "bars",
                    "data": {"symbol": symbols[0], "price": 150.00}
                }
                await self.queue.put_nowait(mock_data)
                logger.info(f"Mock data: {mock_data}")
                await asyncio.sleep(1)  # Simulate delay between updates
            except Exception as e:
                logger.error(f"Error in mock data stream: {e}")



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


    async def health_check(self):
        """
        Periodically checks if the bot is functioning correctly.
        If not, gracefully shuts down or restarts the bot.
        """
        while self.running:
            try:
                # Example checks
                if not self.datastream.is_connected():
                    logger.warning("WebSocket disconnected. Reconnecting...")
                    await self.datastream.connect_with_retries()
                
                # Add more health checks (e.g., queue size, Alpaca API availability)
                if self.queue.qsize() > 1000:
                    logger.warning("Queue size too large. Purging...")
                    await self.purge_queue()

                logger.info("Health check passed.")
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                self.running = False  # Stop the bot to allow for external restart
            await asyncio.sleep(300)  # Run every 5 minutes


    async def run(self):
        """
        Starts the bot for all positions.
        """
        positions = self.alpaca.fetch_positions()
        symbols = list(positions.keys())
        tasks = [
            self.safe_task(self.update_live_data,symbols),    
            self.safe_task(self.monitor_market),
            self.safe_task(self.forward_to_local_server),
            self.safe_task(self.purge_queue),
            self.safe_task(self.health_check)
            ]
        print("In run(), pre gather")
        await asyncio.gather(*tasks) # asyncio.gather(*tasks) collects all the tasks in the list and runs them simultaneously using Python's asyncio framework.
        print("In run(), post gather")


    async def safe_task(self, func, *args):
        try:
            await func(*args)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
                


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

    def signal_handler(signal, frame):
        bot.running = False
        logger.info("Shutting down the bot...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    alpaca = AlpacaAPI(ALPACA_API_KEY, ALPACA_SECRET_KEY)
    datastream_uri = "wss://paper-api.alpaca.markets/stream"
    bot = TradingBot(alpaca, datastream_uri)

    if not bot.is_market_open():
        logger.info("Market is closed. Exiting bot.")
        exit()

    asyncio.run(bot.run())
    print("In main(), post run()")


"""
To add this additional logic to your bot, we need to integrate conditions for:

Track Buy Price-
When the bot executes a buy order, store the buy price for the stock.
Use a dictionary, self.buy_prices, to store the buy prices for each symbol.

Define Sell Conditions-
If the current price drops below the buy price, execute a sell order.
Add an optional threshold percentage to trigger an early sell.

Monitor for Rebound/Rebuy Opportunities-
After selling, watch the stock for an upward trend or percentage recovery from its lowest price.
If the price rises again, issue a buy signal.

Websocket disconnection-
along with the above, think about the case in which we are disconnected midway. 
what can we do to prevent/recover from that?

"""