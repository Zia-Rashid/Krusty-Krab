import requests
import os

class AlpacaAPI:
    def __init__(self, api_key, secret_key, base_url="https://paper-api.alpaca.markets"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.positions = {}

    def update_positions(self, symbol, signal):
        if symbol in self.positions:
            if signal == 1:
                self.positions[symbol] = 1
                return True
            elif signal == -1:
                self.positions[symbol] -= 1
                return True      
               
        else:
            if signal == 1:
                self.positions[symbol] += 1
                return True
            else:
                return False # can't sell something we don't have.

            
    

    def place_order(self, symbol, qty, side="buy", order_type="market", time_in_force="gtc"):
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
