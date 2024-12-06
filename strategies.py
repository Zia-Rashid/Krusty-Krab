def moving_average_crossover(self, symbol, data):
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
        data = self.alpaca.fetch_historical_data(symbol, "2024-10-01")
        signals = []
        for i in range(len(data)):
            if data.iloc[i, 0] > data.iloc[i, 1]:
                signals.append(1)  # BUY signal
            elif data.iloc[i, 0] < data.iloc[i, 1]:
                signals.append(-1)  # SELL signal
            else:
                signals.append(0)  # No signal
        result = np.array(signals)
        returns = (data['c'].pct_change() * result).cumsum()
        return 1 if returns > 0 else -1


####

def mean_reversion_strategy(symbol, data, threshold=0.02):
    """
    Mean reversion strategy based on Bollinger Bands.
    """
    sma = data['c'].rolling(window=20).mean()
    std_dev = data['c'].rolling(window=20).std()
    upper_band = sma + (2 * std_dev)
    lower_band = sma - (2 * std_dev)

    if data['c'].iloc[-1] > upper_band.iloc[-1]:
        return -1  # Sell
    elif data['c'].iloc[-1] < lower_band.iloc[-1]:
        return 1  # Buy
    return 0  # No action
 

#####

def __calculate_volatility__(self, data):
        """
        Calculate Average True Range (ATR) to measure volatility.
        """
        high_low = data['h'] - data['l']
        high_close = abs(data['h'] - data['c'].shift(1))
        low_close = abs(data['l'] - data['c'].shift(1))
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(14).mean()
        return atr.iloc[-1] #Latest ATR value 
def volatility_calculator(self, data):        
    self.backtest_volatility = lambda data, low, high: 1 if low <= (atr := self.calculate_volatility(data)) <= high else -1
    return self.backtest_volatility(data=data, low=2, high=7) 

####

def macd_strategy(symbol, data):
    """
    MACD strategy for buy/sell signals based on moving averages.
    """
    ema12 = data['c'].ewm(span=12, adjust=False).mean()
    ema26 = data['c'].ewm(span=26, adjust=False).mean()
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
    delta = data['c'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    if rsi.iloc[-1] < oversold:
        return 1  # Buy
    elif rsi.iloc[-1] > overbought:
        return -1  # Sell
    return 0  # No action
 
####