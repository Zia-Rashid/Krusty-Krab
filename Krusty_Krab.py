import pandas as pd
import requests
import numpy as np

# Polygon.io API connection
polygon_api_key = "Enter key here"
polygon_base_url = "https://api.polygon.io"

# Define trading strategies
def moving_average_crossover(data):
    """
    Generates buy (1) and sell (-1) signals based on moving average crossover strategy.
    """
    short_window = 20
    long_window = 50

    signals = []
    for i in range(len(data)):
        if data.iloc[i, 0] > data.iloc[i, 1]:  # Short-term average > Long-term average
            signals.append(1)  # BUY signal
        elif data.iloc[i, 0] < data.iloc[i, 1]:  # Short-term average < Long-term average
            signals.append(-1)  # SELL signal
        else:
            signals.append(0)  # No signal
    
    return np.array(signals)  # Return as NumPy array for easier processing


# Backtest the strategy using historical data
def backtest_strategy(data):
    """
    Backtests the moving average crossover strategy.
    """
    signals = moving_average_crossover(data)
    returns = np.cumprod(1 + signals * 0.001) - 1  # Assuming 0.1% per signal for simplicity
    return returns


# Execute buy/sell orders using execution engine API
def execute_order(order_type, quantity):
    """
    Sends buy/sell orders to the trading execution API.
    """
    api_url = f"{polygon_base_url}/v2/orders"
    headers = {"Authorization": f"Bearer {polygon_api_key}"}
    payload = {"type": order_type, "quantity": quantity}

    response = requests.post(api_url, headers=headers, json=payload)
    return response.json()


# Risk management utilities
def calculate_position_value(position, price):
    """
    Calculates the value of the current position based on quantity and price.
    """
    return position * price


def set_stop_loss(position, entry_price, risk_threshold):
    """
    Sets a stop-loss level based on the entry price and acceptable risk threshold.
    """
    stop_loss_price = entry_price * (1 - risk_threshold)
    print(f"Stop-loss set at: {stop_loss_price}")
    return stop_loss_price


# Volatility and trend monitoring
def onHighAlert(current_avg, previous_avg):
    """
    Monitors volatility and identifies potential trend reversals.
    """
    # Check if the short-term trend is above the long-term trend
    if current_avg > previous_avg:
        print("Trend is strong. Holding.")
        return
    
    # Set threshold for drop percentage
    threshold = 5  # 5%

    # Calculate drop percentage
    drop_percentage = (previous_avg - current_avg) / previous_avg * 100

    # Check if the drop exceeds the threshold
    if drop_percentage >= threshold:
        print("Trend has reversed. Sending SELL request...")
        send_sell_request()
    else:
        print(f"Trend is stabilizing. Drop percentage: {drop_percentage:.2f}%")


# Update moving averages and monitor for alerts
def update_averages(current_data, short_window, long_window):
    """
    Updates short and long moving averages and triggers alert checks.
    """
    current_avg = current_data.iloc[-short_window:].mean()
    previous_avg = current_data.iloc[-long_window:].mean()
    
    # Check for trend volatility or reversals
    onHighAlert(current_avg, previous_avg)
    return current_avg, previous_avg


# Send a sample sell request (mock for demo purposes)
def send_sell_request():
    print("Mock SELL request sent.")
