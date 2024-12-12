import pandas as pd
import numpy as np
import TradingBot as bot
import logging
# import AlpacaAPI as alpaca
# from AlpacaAPI import *
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Strategies")#="TradingBot"
logger.setLevel(logging.INFO)


def moving_average_crossover(symbol, data):
        """
        Strategy: Generate buy (1) and sell (-1) signals based on moving average crossover.
        """
        """ 
        This provides the actual daily return for the asset.
            * signals: Multiplies the daily return by the corresponding signal to apply the trading strategy:
            A signal of 1 means you profit (or lose) based on the price movement.
            A signal of -1 means you gain if the price falls (short-selling).
            A signal of 0 means no position is taken, so the return is 0.
            .cumsum(): Computes the cumulative sum of the returns over time, reflecting the overall performance of the strategy.
            """
        #data = alpaca.fetch_historical_data(symbol, "2024-10-01")

        if data.empty or 'close' not in data.columns:
            print("Data for moving average crossover is missing or incomplete.")
            return 0 

        signals = []
        for i in range(len(data)):
            if data.iloc[i, 0] > data.iloc[i, 1]:
                signals.append(1)  # BUY signal
            elif data.iloc[i, 0] < data.iloc[i, 1]:
                signals.append(-1)  # SELL signal
            else:
                signals.append(0)  # No signal
        result = np.array(signals)
        returns = (data['close'].pct_change() * result).cumsum()
        return 1 if returns.iloc[-1] > 0 else -1


####

def mean_reversion_strategy(symbol, data, threshold=0.02):
    """
    Mean reversion strategy based on Bollinger Bands.
    """
    sma = data['close'].rolling(window=20).mean()
    std_dev = data['close'].rolling(window=20).std()
    upper_band = sma + (2 * std_dev)
    lower_band = sma - (2 * std_dev)

    if data['close'].iloc[-1] > upper_band.iloc[-1]:
        return -1  # Sell
    elif data['close'].iloc[-1] < lower_band.iloc[-1]:
        return 1  # Buy
    return 0  # No action
 

#####

def __calculate_volatility__(data):
    if len(data) < 14:  # Ensure at least 14 rows for the rolling calculation
        logger.warning("Insufficient data for volatility calculation.")
        return float('nan')
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift(1))
    low_close = abs(data['low'] - data['close'].shift(1))
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(14).mean()
    return atr.iloc[-1]  # Latest ATR value

def volatility_calculator(self, data):
    atr = __calculate_volatility__(data)
    if pd.isna(atr):  # Handle cases where ATR cannot be calculated
        logger.warning("ATR calculation failed. Returning -1.")
        return -1
    low, high = data['high'].min() * 0.01, data['high'].max() * 0.05  # Example dynamic bounds
    return 1 if low <= atr <= high else -1

####

def macd_strategy(symbol, data):
    """
    MACD strategy for buy/sell signals based on moving averages.
    """
    ema12 = data['close'].ewm(span=12, adjust=False).mean()
    ema26 = data['close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()

    if macd.iloc[-1] > signal.iloc[-1]:
        return 1  # Buy
    elif macd.iloc[-1] < signal.iloc[-1]:
        return -1  # Sell
    return 0  # No action

####

def rsi_strategy(symbol, data, overbought=70, oversold=30):
    """
    RSI strategy to identify overbought or oversold conditions.
    """
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    if rsi.iloc[-1] < oversold:
        #print(rsi.iloc[-1])
        return 1  # Buy
    elif rsi.iloc[-1] > overbought:
        #print(rsi.iloc[-1])
        return -1  # Sell
    return 0  # No action
 
####