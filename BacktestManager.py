import TradingBot
import numpy as np
import pandas as pd


class BacktestManager:

    def __init__(self):
        self.strategies = []

    def add_strategy(self, strategy):
        self.strategies.append(strategy)

    def execute_strategies(self, symbol, data):
        """
        Runs all strategies and returns the net decision score.
        """
        result = sum(strategy(symbol, data) for strategy in self.strategies)
        return result



    
