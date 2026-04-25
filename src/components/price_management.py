import yfinance as yf

# Ticker laden
akan = yf.Ticker("AKAN")

# Historie mit auto_adjust=False abrufen
# So bleiben die 'Close'-Werte die echten historischen Werte
df = akan.history(period="6mo", auto_adjust=False)

print(df[['Close', 'Adj Close']].tail(10))
