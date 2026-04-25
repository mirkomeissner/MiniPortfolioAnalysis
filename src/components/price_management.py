import yfinance as yf
import pandas as pd
import streamlit as st

def price_table_view():
    st.title("Price Data Overview")
    
    # Eingabe-Felder für den User (optional, macht es aber flexibler)
    col1, col2 = st.columns(2)
    with col1:
        ticker_symbol = st.text_input("Ticker Symbol", value="AKAN")
    with col2:
        period = st.selectbox("Zeitraum", ["1mo", "3mo", "6mo", "1y", "max"], index=0)
    
    # Daten abrufen
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period=period, auto_adjust=False)
    
    if df.empty:
        st.error(f"Keine Daten für {ticker_symbol} gefunden.")
        return

    # Daten aufbereiten
    view_df = df[['Close', 'Adj Close', 'Stock Splits']].copy()
    
    # Formatierung für die Anzeige (Datum schöner machen)
    view_df.index = view_df.index.strftime('%Y-%m-%d')
    
    # Erklärung für den User
    st.info("**Close:** Unbereinigter historischer Kurs | **Adj Close:** Bereinigter Kurs (Split-korrigiert)")

    # Die Tabelle in Streamlit anzeigen
    st.dataframe(view_df.sort_index(ascending=False), use_container_width=True)

    # Optional: Highlight bei Split-Events
    splits = view_df[view_df['Stock Splits'] != 0]
    if not splits.empty:
        st.warning("Achtung: In diesem Zeitraum fand ein Split statt!")
        st.write(splits)
