import os
import requests

class MockTiingo:
    """Simuliert die Tiingo-API-Antworten für die Entwicklung."""
    def __init__(self, ticker_symbol):
        self.ticker_symbol = ticker_symbol
        
    def get_latest_price(self):
        # Liefert Mock-Daten zurück
        return {
            "price": 124.50,
            "currency": "USD" if not self.ticker_symbol.endswith(".DE") else "EUR"
        }

class MyTiingoProxy:
    """
    Proxy für die Tiingo-API. 
    Entscheidet anhand von APP_ENV, ob Live- oder Mock-Daten geliefert werden.
    """
    @property
    def is_dev(self) -> bool:
        return os.getenv("APP_ENV", "main").lower() == "dev"

    def get_latest_price(self, ticker_symbol):
        if self.is_dev:
            mock = MockTiingo(ticker_symbol)
            return mock.get_latest_price()
        
        # --- LIVE API CALL ---
        # Ersetze dies durch deinen echten API-Token / Endpunkt bei Bedarf
        api_token = os.getenv("TIINGO_API_KEY", "YOUR_DEFAULT_TOKEN")
        url = f"https://api.tiingo.com/tiingo/daily/{ticker_symbol}/prices"
        headers = {'Content-Type': 'application/json', 'Authorization': f'Token {api_token}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200 and response.json():
                data = response.json()[0]
                # Tiingo liefert standardmäßig Schlusskurse; Währung ist meist USD (außer bei speziellen Feeds)
                return {
                    "price": data.get("close"),
                    "currency": "USD" # Kann je nach Tiingo-Asset angepasst werden
                }
            return {"price": None, "currency": None}
        except Exception:
            return {"price": None, "currency": None}

# Singleton Instanz
my_tiingo = MyTiingoProxy()
