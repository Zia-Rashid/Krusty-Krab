import requests


class PolygonAPI:
    def __init__(self,api_key):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"

    def get_historical_data(self, symbol, start_date, end_date):
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}"
        params = {"adjusted":"true", "apiKey":self.api_key}
        response = requests.get(url,params=params)
        if response.status_code == 200:
            return response.json()["results"]
        else:
            raise Exception(f"Polygon API error: {response.status_code}, {response.text}")
        