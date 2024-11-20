import requests
import time 
import pandas as pd
import threading
from datetime import datetime, timedelta

class AlpacaAPI:
    def __init__(self, api_key, secret_key, base_url="https://paper-api.alpaca.markets"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.positions = {}


    def fetch_positions(self):
        """
        Fetch current postions and their quantity from Alpaca
        """
        url = f"{self.base_url}/v2/positions"
        headers = { 
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            self.positions = {pos['symbol'] : int(pos['qty']) for pos in response.json()} 
        else:
            raise Exception(f"Error fetching positions: {response.status_code}, {response.text}")
            

    def place_order(self, symbol, qty, side="buy", order_type="market", time_in_force="gtc"):
        """
        Place an order through Alpaca
        """
        url = f"{self.base_url}/v2/orders"
        headers = { 
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key
        }
        payload = {
            "symbol":symbol,
            "qty":qty,
            "side":side,
            "type": order_type,
            "time_in_force": time_in_force,
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"Order placed: {response.json()}!")
        else:
            raise Exception(f"Alpaca API error: {response.status_code}, {response.text}")
        
    
    def fetch_market_data(self, symbol, start_date, end_date):
        """
        Fetch historical data from Alpaca
        """
        url = f"{self.base_url}/v2/orders"
        headers = { 
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key
        }
        params = {
            "start" : start_date,
            "end" : end_date,
            "timeframe" : "1Day"
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
           return response.json()['bars']
        else:
            raise Exception(f"Error fetching market data: {response.status_code}, {response.text}")