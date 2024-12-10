import datetime
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
from datetime import date, timezone, datetime
import BacktestManager
from BacktestManager import BacktestManager
from strategies import *
from Posman import Posman

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TradingBot")#="TradingBot"
logger.setLevel(logging.INFO)

#debug_mode = False  # Set to True for detailed logs
#logger.setLevel(logging.DEBUG if debug_mode else logging.WARNING)


# file_handler = logging.FileHandler('/var/log/tradingbot.activity')
# file_handler.setLevel(logging.INFO)
# file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

# logger.addHandler(file_handler)


class TradingBot:
    def __init__(self, alpaca_api, backtests=None, posman=None):
        """
        Initialize TradingBot with Alpaca API keys and create an Alpaca API instance.
        """
        self.alpaca = alpaca_api
        self.btm = backtests
        self.posman = posman
        self.logger = logger
        self.running = True
        self.lock = threading.Lock()
        

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
                logger.debug(f"Fetched positions: {positions}")      
                if not positions:
                    logger.info("No positions to monitor")
                    asyncio.sleep(60)
                    continue

                for symbol, (qty,current_price) in positions.items():
                    logger.info(f"Monitoring {symbol}: qty={qty}, price={current_price}")

                    if symbol in self.alpaca.checkbook:
                        buy_price = self.alpaca.checkbook[symbol]
                        if current_price < self.posman.calculate_stop_loss(buy_price) or current_price > buy_price * 2.5: # sell if it is a loss
                            # in the future change htis to the price that it was yesterday or 
                            # maybe a week ago and I should have logic that tracks the symbol to 
                            # see if the value starts to turn around and i should rebuy it.
                            #print("Selling")
                            try:
                                self.execute_trades(-1, symbol=symbol) 
                            except Exception as e:
                                logger.error(f"Error placing SELL order for {symbol}: {e}")
                        elif self.backtest_strategy(symbol=symbol):             # buy if it is advantageous
                            #print("Buying)")
                            logger.debug(f"Running backtest for {symbol} with price {current_price} and buy price {self.alpaca.checkbook[symbol]}")
                            try:
                                self.execute_trades(1, symbol=symbol) 
                            except Exception as e:
                                logger.error(f"Error placing BUY order for {symbol}: {e}")
                        else:
                            print("Skipping\n")
                            continue
                    else:
                        logger.warning(f"{symbol} not found in checkbook during monitoring.")
                           

                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error monitoring market: {e}")


    def backtest_strategy(self, symbol):
        """
        Backtests market conditions to make trade decisions
        """
        #raw_data = pd.Series(self.alpaca.fetch_raw_data(symbol))
        try:
            raw_data = self.alpaca.fetch_historical_data(symbol,"2024-10-01")
            if raw_data.empty:
                logger.warning(f"No historical data for {symbol}.")
                return False
            if not {'close', 'high', 'low'}.issubset(raw_data.columns):
                raise ValueError("Required columns ('close', 'high', 'low') are missing in data.")

        except Exception as e:
            logger.error(f"Error in backtest_strategy: {e}")
            return False
        
        logger.info(f"Running backtest strategies for {symbol}...")
        decision = btm.execute_strategies(symbol, raw_data)
        logger.info(f"Backtest result for {symbol} at {datetime.now()}: -BUY- {decision}") if decision > (len(btm.strategies) // 2) else logger.info(f"Backtest result for {symbol} at {datetime.now()}: -HOLD- {decision}")
        return decision > (len(btm.strategies) // 2)

    def execute_trades(self, signal, symbol):
        """
        Execute trades based on the signal. Signal:
        <>  1: Buy
        <> -1: Sell
        """
        with self.lock:
            self.alpaca.fetch_positions()
            logger.info(f"Processing signal {signal} for {symbol}")
            logger.debug(f"Signal {signal} for {symbol}, attempting to place order.")

            if signal == 1:  # BUY
                qty = 1
                logger.info(f"Placing BUY order for {symbol}")
                self.alpaca.place_order(symbol, qty=qty, side="buy")
                # Update Checkbook
                position = self.alpaca.positions.get(symbol)
                if position:
                    self.alpaca.checkbook[symbol] = position[1]

            elif signal == -1:  # SELL
                logger.info(f"Placing SELL order for {symbol}")
                self.alpaca.place_order(symbol, qty=1, side="sell")
                #Update Checkbook
                if symbol in self.alpaca.checkbook:
                    del self.alpaca.checkbook[symbol]

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
    bot.alpaca.populate_checkbook()
    posman = Posman(bot)
    bot.__setPosman__(posman)
    portfolio_value = bot.alpaca.calculate_portfolio_value()
    available_cash = bot.posman.available_funds()
    btm = BacktestManager([
            moving_average_crossover,
                volatility_calculator,
                    macd_strategy,
                        mean_reversion_strategy,
                            rsi_strategy,
                                (lambda symbol, data: bot.posman.position_sizing_strategy(symbol, portfolio_value, available_cash))
                                    ], bot)
    bot.__setBacktestManager__(btm)

    if not bot.is_market_open():
        logger.info("Market is closed. Exiting bot.")
        exit()

    asyncio.run(bot.run())
    # END REAL **********
