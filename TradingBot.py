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
import Posman

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)#="TradingBot"
logger.setLevel(logging.DEBUG)

class TradingBot:
    def __init__(self, alpaca_api, backtests=None, posman=None):
        """
        Initialize TradingBot with Alpaca API keys and create an Alpaca API instance.
        """
        self.alpaca = alpaca_api
        self.btm = backtests
        self.posman = posman
        self.running = True
        self.lock = threading.Lock()
        self.checkbook = {}  # Track buy prices for symbols # <--- To be Implemented

    def __setPosman__(self, posman):
        """
        securely integrates position manager
        """
        self.posman = posman


    def __setBacktestManager__(self, btm):
        """
        securely integrates backtest manager
        """
        self.btm = btm


    def is_market_open(self):
        """
        checks if the stock market is open
        """
        try:
            api = trade_api.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://paper-api.alpaca.markets")
            clock = api.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False


    async def update_live_data(self):
        """
        periodically fetches updated market data
        """
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
                        if current_price < self.posman.calculate_stop_loss(buy_price): # sell if it is a loss
                            try:
                                self.execute_trades(-1, symbol=symbol) 
                            except Exception as e:
                                logger.error(f"Error placing SELL order for {symbol}: {e}")
                        elif self.backtest_strategy(symbol=symbol):             # buy if it is advantageous
                            try:
                                self.execute_trades(1, symbol=symbol) 
                            except Exception as e:
                                logger.error(f"Error placing BUY order for {symbol}: {e}")   

                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error monitoring market: {e}")


    def backtest_strategy(self, symbol):
        """
        Backtests market conditions to make trade decisions
        """
        raw_data = pd.Series(self.alpaca.fetch_raw_data(symbol))
        portfolio_value = self.alpaca.calculate_portfolio_value()
        available_cash = self.posman.available_funds()

        self.btm.add_strategy(moving_average_crossover)
        self.btm.add_strategy(volatility_calculator)
        self.btm.add_strategy(mean_reversion_strategy)
        self.btm.add_strategy(macd_strategy)
        self.btm.add_strategy(rsi_strategy)
        self.btm.add_strategy(lambda symbol, data: self.posman.position_sizing_strategy(symbol, portfolio_value, available_cash))

        logger.info(f"Running backtest strategies for {symbol}...")
        decision = btm.execute_strategies(symbol, raw_data)

        logger.info(f"Backtest result for {symbol}: {decision}")
        return decision > len(btm.strategies // 2)
    

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


    async def run(self):
        """
        Starts the bot for all positions.
        """
        #positions = self.alpaca.fetch_positions()
        #symbols = list(positions.keys())
        tasks = [
            self.safe_task(self.update_live_data),    
            self.safe_task(self.monitor_market),
            ]
        await asyncio.gather(*tasks)

    async def safe_task(self, func, *args):
        """
        runs the tasks in an environment that will deal with any errors that arise
        """
        try:
            await func(*args)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")  
            self.running = False


if __name__ == "__main__":
    
    def signal_handler(signal, frame):
        """
        gracefully terminate the bot
        """
        bot.running = False
        logger.info("Shutting down the bot...")
        print(f"Portfolio value: {bot.alpaca.calculate_portfolio_value()}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # START REAL ********
    alpaca = AlpacaAPI(ALPACA_API_KEY, ALPACA_SECRET_KEY)
    bot = TradingBot(alpaca)
    bot.__setPosman__ = Posman(bot)
    bot.__setBacktestManager__ = btm = BacktestManager([
                                           moving_average_crossover,
                                               volatility_calculator,
                                                   mean_reversion_strategy,
                                                       rsi_strategy
                                                           ], bot)

    if not bot.is_market_open():
        logger.info("Market is closed. Exiting bot.")
        exit()

    asyncio.run(bot.run())
    # END REAL **********
