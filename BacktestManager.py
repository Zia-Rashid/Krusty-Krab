import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BackTestManager")#="TradingBot"
logger.setLevel(logging.INFO)

class BacktestManager:

    def __init__(self, strategies, bot):
        self.strategies = strategies
        self.main_bot = bot

    def add_strategy(self, strategy):
        """
        Add a strategy to be used in backtests
        """
        self.strategies.append(strategy)

    def execute_strategies(self, symbol, data):     
        logger.debug(f"Running backtesting strategies for {symbol}")
        total_score = 0
        for strategy in self.strategies:
            result = strategy(symbol, data)
            print(f"Strategy {strategy.__name__} returned {result} for {symbol}")
            total_score += result
        return total_score





    
