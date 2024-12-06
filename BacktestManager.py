import TradingBot
import numpy as np
import pandas as pd


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
        """
        Runs all backtesting strategies and returns the net decision score.
        """
        for strategy in self.strategies:
            result = strategy(symbol, data)
            self.main_bot.logger.info(f"Strategy: {strategy.__name__}, Symbol: {symbol}, Result: {result}") # may or may not cause errors LOL
        return sum(result)        



    
