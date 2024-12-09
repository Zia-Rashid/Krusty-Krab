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
        """
        Runs all backtesting strategies and returns the net decision score.
        """
        logger.debug(f"Running backtesting strategies")
        decision_score = sum(strategy(symbol, data) for strategy in self.strategies)
        return decision_score




    
