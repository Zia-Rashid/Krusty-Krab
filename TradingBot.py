import signal
import numpy as np
import AlpacaAPI
from AlpacaAPI import *
import asyncio
import pandas as pd
import threading
from config import ALPACA_API_KEY
from config import ALPACA_SECRET_KEY
import logging
import sys
import alpaca_trade_api as trade_api
from datetime import date
import BacktestManager
from strategies import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)#="TradingBot"
logger.setLevel(logging.DEBUG)

class TradingBot:
    def __init__(self, alpaca_api):
        """
        Initialize TradingBot with Alpaca API keys and create an Alpaca API instance.
        """
        self.alpaca = alpaca_api
        self.running = True
        self.lock = threading.Lock()
        self.queue = asyncio.Queue(maxsize=1000)  # Queue for sharing data_update output.
        #self.datastream = Datastream(datastream_uri) #datastream instance for websockets
        self.checkbook = {}  # Track buy prices for symbols # <--- To be Implemented

    def is_market_open(self):
        try:
            api = trade_api.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://paper-api.alpaca.markets")
            clock = api.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False



    async def update_live_data(self):
        while self.running:
            if not self.is_market_open():
                logger.info("Market is closed. Skipping live data updates...")  
                asyncio.sleep(60)  # loop condition, as averse to 'return'
                continue  
            
            try:
                # Fetch positions
                self.alpaca.fetch_positions()
                logger.info("Fetched positions succesfully")
            except Exception as e:
                logger.error(f"Error fetching live data: {e}")

            await asyncio.sleep(30)


    async def purge_queue(self):
        while self.running:
            try:
                while not self.queue.empty():
                    await self.queue.get_nowait()  # Clear one item
                await asyncio.sleep(60)  # Run every 60 seconds
            except Exception as e:
                logger.error(f"Error purging queue: {e}")
        

    def backtest_strategy(self, symbol):
        """
        Backtests market conditions to make trade decisions
        """
        btm = BacktestManager()
        raw_data = pd.Series(self.alpaca.fetch_raw_data(symbol))
        portfolio_value = self.alpaca.calculate_portfolio_value()
        available_cash = self.available_funds()

        btm.add_strategy(moving_average_crossover)
        btm.add_strategy(volatility_calculator)
        btm.add_strategy(mean_reversion_strategy)
        btm.add_strategy(macd_strategy)
        btm.add_strategy(rsi_strategy)
        btm.add_strategy(lambda symbol, data: self.position_sizing_strategy(symbol, portfolio_value, available_cash))

        logger.info(f"Running backtest strategies for {symbol}...")
        decision = btm.execute_strategies(symbol, raw_data)

        logger.info(f"Backtest result for {symbol}: {decision}")
        return decision > len(btm.strategies - 1 // 2)

    
    def execute_trades(self, signal, symbol):
        """
        Execute trades based on the signal. Signal:
        <>  1: Buy
        <> -1: Sell
        """
        with self.lock:
            self.alpaca.fetch_positions()
            logger.info(f"Processing signal {signal} for {symbol}")

            if signal == 1:  # BUY
                qty = 1
                logger.info(f"Placing BUY order for {symbol}")
                self.alpaca.place_order(symbol, qty=qty, side="buy")
                # Update Checkbook
                position = self.alpaca.positions.get(symbol)
                if position:
                    self.checkbook[symbol] = position[1]

            elif signal == -1:  # SELL
                logger.info(f"Placing SELL order for {symbol}")
                self.alpaca.place_order(symbol, qty=1, side="sell")
                #Update Checkbook
                if symbol in self.checkbook and self.checkbook[symbol]:
                    sold_price = self.checkbook[symbol].pop(len(self.checkbook[symbol])-1)   
                    logger.info(f"Sold {symbol} at {sold_price}")
                    if not self.checkbook[symbol]:  # If the list is now empty
                        del self.checkbook[symbol]

            print(f"Trade for {symbol} completed. Notifying other threads.")

    '''
    def evaluate_market_conditions(self, data, symbol):     # lets turn this into a nubmer from 1 to 10, and if it is above 8, it will be considered a highly volatile stock and should be dealt with differently
        """
        Analyze market trends and make action decisions.
        """
        short_avg = data['c'].rolling(20).mean().iloc[-1]
        long_avg = data['c'].rolling(50).mean().iloc[-1]
        current_price = data['c'].iloc[-1]
        atr = self.calculate_volatility(data) #incorporate this volatility in the future.

        stop_loss_price = self.calculate_stop_loss(entry_price=current_price, risk_threshold=0.05)

        # Decision logic
        if short_avg > long_avg and current_price > stop_loss_price:
            return "buy", 1
        if current_price < stop_loss_price:
            return "sell", self.alpaca.positions[symbol]
        elif short_avg < long_avg:
            if symbol in self.alpaca.positions and current_price < (self.alpaca.positions[symbol] * 0.95):
                return "sell", self.alpaca.positions[symbol]
        else:
            return None, 0
    '''

    async def monitor_market(self):
        """
        A method to monitor market conditions for all symbols.
        """  
        while self.running:
            try:
                positions = self.alpaca.fetch_positions()         
                if not positions:
                    logger.info("No positions to monitor")
                    asyncio.sleep(60)
                    continue

                for symbol, (qty,current_price) in positions.items():
                    logger.info(f"Monitoring {symbol}: qty={qty}, price={current_price}")

                    if symbol in self.checkbook:
                        buy_price = self.checkbook[symbol]
                        if current_price < self.calculate_stop_loss(buy_price): # sell if it is a loss
                            self.execute_trades(-1, symbol=symbol) 
                        elif self.backtest_strategy(symbol=symbol):             # buy if it is advantageous
                            if len(self.checkbook[symbol]) <= 10:               # limit number of stocks
                                self.execute_trades(1,symbol=symbol)   

                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error monitoring market: {e}")

    '''
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
    '''

    async def health_check(self):
        """
        Periodically checks if the bot is functioning correctly.
        If not, gracefully shuts down or restarts the bot.
        """
        while self.running:
            try:
                # Example checks
                if not self.datastream.connection:
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
        #positions = self.alpaca.fetch_positions()
        #symbols = list(positions.keys())
        tasks = [
            self.safe_task(self.update_live_data),    
            self.safe_task(self.monitor_market),
            self.safe_task(self.purge_queue),
            self.safe_task(self.health_check)
            ]
        await asyncio.gather(*tasks)
    

    async def safe_task(self, func, *args):
        try:
            await func(*args)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")  


    def available_funds(self):
        cash = self.alpaca.calculate_portfolio_value()
        positions = self.alpaca.fetch_positions()
        for symbol in positions:
            cash -= self.calculate_position_value(symbol=symbol)
        return cash
        

    def calculate_position_value(self, symbol):
        """
        Calculate the value of a position (quantity * price).
        """
        qty = self.alpaca.positions.get(symbol)[0]
        price = self.alpaca.positions.get(symbol)[1]
        return qty * price  # Adjust for slippage
    
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
    

if __name__ == "__main__":
    
    async def signal_handler(signal, frame):
        bot.running = False
        logger.info("Shutting down the bot...")
        print(f"Portfolio value: {bot.alpaca.calculate_portfolio_value()}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # START REAL ********
    alpaca = AlpacaAPI(ALPACA_API_KEY, ALPACA_SECRET_KEY)
    bot = TradingBot(alpaca)

    if not bot.is_market_open():
        logger.info("Market is closed. Exiting bot.")
        exit()

    asyncio.run(bot.run())
    # END REAL **********

"""
To add this additional logic to your bot, we need to integrate conditions for:

Monitor for Rebound/Rebuy Opportunities-
After selling, watch the stock for an upward trend or percentage recovery from its lowest price.
If the price rises again, issue a buy signal.

Increase positions-
One of the most important things that I have to implement is a method to determine whether or not
to buy more stock. I should have pull my portfolio value, my unallocated amount(probably math done by subtracting 
actively owned stock), and using moving average and something more advanced. Ideally the decision should go through
about 3 backtests with an affirmative result before a trade is executed

"""