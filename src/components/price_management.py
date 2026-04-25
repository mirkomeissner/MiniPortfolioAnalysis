import yfinance as yf
import pandas as pd

def price_table_view():
    """
    Erstellt eine Tabelle der Schlusskurse (unbereinigt vs. bereinigt).
    
    :param ticker_symbol: Das Kürzel der Aktie (z.B. 'AKAN')
    :param period: Zeitraum (z.B. '1mo', '3mo', '1y')
    """
    # Ticker Objekt initialisieren
    ticker_symbol="AKAN"
    period="1mo"    
    ticker = yf.Ticker(ticker_symbol)
    
    # Historie laden: auto_adjust=False ist entscheidend für unbereinigte Kurse
    df = ticker.history(period=period, auto_adjust=False)
    
    if df.empty:
        return f"Keine Daten für {ticker_symbol} gefunden."

    # Wir extrahieren die relevanten Spalten:
    # 'Close' = Der echte Preis, der damals an der Börse stand
    # 'Adj Close' = Der durch yfinance rückwirkend für Splits/Dividenden geglättete Preis
    view_df = df[['Close', 'Adj Close']].copy()
    
    # Optional: Den Split-Faktor zur Veranschaulichung anzeigen
    # yfinance liefert in 'Stock Splits' das Verhältnis (z.B. 0.222 für 1:4.5)
    view_df['Split_Event'] = df['Stock Splits']
    
    # Formatierung für die Ausgabe
    pd.options.display.float_format = '{:.4f}'.format
    
    print(f"--- Preishistorie für {ticker_symbol} ({period}) ---")
    print("Close:     Echter historischer Kurs (unbereinigt)")
    print("Adj Close: Rückwirkend bereinigter Kurs (für Analysen)")
    print("-" * 50)
    
    return view_df

