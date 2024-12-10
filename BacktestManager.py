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
        total_weight = 0
        
        for strategy, weight in self.strategies:
            result = strategy(symbol, data)
            total_score += result * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
