import io
import os
import sys
import pandas as pd
from datetime import date, datetime

import src.database as database
database.initialize_runtime_from_env(strict=False)
from src.utils import (
    my_ishares,
    normalize_float,
    normalize_date,
    reconcile_asset_price_data,
    parse_iso_date,
    empty_provider_result,
    persist_price_records,
    process_provider_batch,
)


def _download_excel(ticker: str, currency: str, retries: int = 3, timeout: int = 15) -> bytes:
    return my_ishares.fetch_excel_bytes(
        ticker=ticker,
        currency=currency,
        retries=retries,
        timeout=timeout,
    )



def import_ishares_history_for_ticker(isin: str, ticker: str, price_currency: str, price_start_date: str = None,
                                     dry_run: bool = False, excel_bytes: bytes = None,
                                     request_start_date: str = None, asset_start_date: str = None):
    """
    Downloads and imports ISH price history for a single asset.

    Parameters
    - isin, ticker: identifiers
    - price_currency: e.g. 'USD'
    - price_start_date: ISO date string to trim history (optional)
    - dry_run: if True, parsing is performed but DB upserts are skipped
    - excel_bytes: optional raw bytes for tests to bypass network

    Returns a dict with summary: {'parsed': n, 'inserted': n, 'updated': n}
    """
    # Normalize boundaries used by new incremental logic
    request_start = parse_iso_date(request_start_date)
    asset_start = parse_iso_date(asset_start_date) or parse_iso_date(price_start_date)

    # Note: iShares doesn't have an API key requirement, so only validate ticker and asset_start
    if not ticker:
        return {"error": "missing_ticker"}
    if asset_start is None:
        return {"error": "missing_asset_start"}

    # 1) download or use provided bytes
    if excel_bytes is None:
        try:
            excel_bytes = _download_excel(ticker, price_currency)
            
        except Exception as e:
            print(f"Failed to download Excel for {ticker}: {e}")
            return {"error": str(e)}

    # 2) read required sheets
    try:
        # First, handle Microsoft SpreadsheetML XML format (some iShares downloads use it)
        raw = excel_bytes
        # strip repeated UTF-8 BOMs
        bom = b'\xef\xbb\xbf'
        while raw.startswith(bom):
            raw = raw[len(bom):]
        if raw.lstrip().startswith(b'<?xml'):
            # Parse XML Spreadsheet (SpreadsheetML)
            import xml.etree.ElementTree as ET
           
            text = raw.decode('utf-8', errors='ignore')
            
            # --- REPARATUR VON UNMASKIERTEN UND-ZEICHEN (&) ---
            import re
            # Ersetzt ein '&', dem KEIN gültiges XML-Entity (wie &amp;, &lt;, &gt;) folgt, durch &amp;
            text = re.sub(r'&(?!(amp|lt|gt|quot|apos);)', '&amp;', text)
            
            # Parse XML Spreadsheet (SpreadsheetML)
            import xml.etree.ElementTree as ET
            try:
                tree = ET.fromstring(text)
            except ET.ParseError as xml_err:
                print(f"XML-Parsing-Fehler trotz Bereinigung bei {ticker}: {xml_err}")
                # Optionaler zweiter Rettungsversuch: Komplett nacktes XML erzwingen
                raise xml_err

            
            # remove namespace helper
            def _strip_ns(tag):
                return tag[tag.find('}')+1:] if '}' in tag else tag
            sheets = {}
            for ws in tree.findall('.//'):
                pass
            # More robust approach: find all Worksheet elements by local-name
            worksheets = []
            for elem in tree.iter():
                if _strip_ns(elem.tag).lower() == 'worksheet':
                    worksheets.append(elem)
            for ws in worksheets:
                name = ws.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Name') or ws.attrib.get('Name') or ws.attrib.get('name')
                # find Table child
                table = None
                for c in ws:
                    if _strip_ns(c.tag).lower() == 'table':
                        table = c
                        break
                rows = []
                if table is not None:
                    for r in table:
                        if _strip_ns(r.tag).lower() != 'row':
                            continue
                        cells = []
                        col_idx = 0
                        for cell in r:
                            if _strip_ns(cell.tag).lower() != 'cell':
                                continue
                            # handle ss:Index (sparse cells)
                            idx = None
                            for k in cell.attrib.keys():
                                if k.lower().endswith('index'):
                                    try:
                                        idx = int(cell.attrib[k]) - 1
                                    except Exception:
                                        idx = None
                                    break
                            if idx is not None:
                                col_idx = idx
                            # find Data child
                            cell_text = None
                            for d in cell:
                                if _strip_ns(d.tag).lower() == 'data':
                                    cell_text = d.text
                                    break
                            # ensure list is large enough
                            if col_idx >= len(cells):
                                cells.extend([None] * (col_idx - len(cells) + 1))
                            cells[col_idx] = cell_text
                            col_idx += 1
                        rows.append(cells)
                # First row = header
                if rows:
                    import pandas as _pd
                    header = rows[0]
                    data_rows = rows[1:]
                    # Debug: ensure header length matches data width
                    max_len = max((len(r) for r in data_rows), default=0)
                    # pad header or rows as needed
                    if len(header) < max_len:
                        header = header + [f"col_{i}" for i in range(len(header), max_len)]
                    data_rows = [r + [None] * (len(header) - len(r)) if len(r) < len(header) else r[:len(header)] for r in data_rows]
                    df = _pd.DataFrame(data_rows, columns=header)
                else:
                    import pandas as _pd
                    df = _pd.DataFrame()
                sheets[name or 'Sheet'] = df
            xls = sheets
        else:
            # Detect file header to pick an engine: ZIP (xlsx) vs OLE (xls)
            header = excel_bytes[:4]
            engine = None
            if header.startswith(b'PK'):
                engine = 'openpyxl'
            elif header == b'\xD0\xCF\x11\xE0':
                engine = 'xlrd'

            if engine:
                xls = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=["Historisch", "Ausschüttungen"], engine=engine)
            else:
                # Fallback: try xlrd then openpyxl
                try:
                    xls = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=["Historisch", "Ausschüttungen"], engine='xlrd')
                except Exception:
                    xls = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=["Historisch", "Ausschüttungen"], engine='openpyxl')
    except Exception as e:
        print(f"Error parsing Excel for {ticker}: {e}")
        return {"error": str(e)}

    # 3) extract historisch
    hist = xls.get("Historisch")
    if hist is None:
        print(f"Sheet 'Historisch' not found for {ticker}")
        return {"error": "missing_sheet"}

    # Normalize expected columns (case-insensitive)
    hist_cols = {c.lower(): c for c in hist.columns}
    if "per" not in hist_cols or "nav" not in hist_cols or "währung" not in hist_cols:
        print(f"Required columns not found in 'Historisch' for {ticker}: {list(hist.columns)}")
        return {"error": "missing_columns"}

    per_col = hist_cols["per"]
    nav_col = hist_cols["nav"]
    curr_col = hist_cols["währung"]

    hist_df = hist[[per_col, nav_col, curr_col]].rename(columns={per_col: "per", nav_col: "NAV", curr_col: "Währung"})
    hist_df = hist_df.dropna(subset=["per"]).copy()
    # Robust date parsing for German/English month names like '17.Juni2026' or '17.Apr.2026'
    import re
    month_map = {
        'januar': '01', 'jan': '01',
        'februar': '02', 'feb': '02',
        'märz': '03', 'maerz': '03', 'mar': '03', 'mrz': '03',
        'april': '04', 'apr': '04',
        'mai': '05', 'may': '05',
        'juni': '06', 'jun': '06',
        'juli': '07', 'jul': '07',
        'august': '08', 'aug': '08',
        'september': '09', 'sep': '09', 'sept': '09',
        'oktober': '10', 'okt': '10', 'oct': '10',
        'november': '11', 'nov': '11',
        'dezember': '12', 'dez': '12', 'dec': '12'
    }
    def _parse_date_str(s):
        if s is None:
            return None
        s0 = str(s).strip()
        low = s0.lower()
        # remove unwanted spaces
        for k, v in month_map.items():
            if k in low:
                # replace the month token with its number
                low2 = re.sub(k, v, low, count=1)
                # keep only digits and dots
                low2 = re.sub(r'[^0-9\.]', '.', low2)
                low2 = re.sub(r'\.+', '.', low2).strip('.')
                parts = low2.split('.')
                if len(parts) >= 3:
                    day = parts[0]
                    month = parts[1]
                    year = parts[-1]
                    try:
                        return datetime.strptime(f"{day}.{month}.{year}", "%d.%m.%Y").date()
                    except Exception:
                        break
        # fallback to pandas parser
        try:
            if len(s0) >= 10 and s0[4] == '-' and s0[7] == '-':
                return datetime.fromisoformat(s0[:10]).date()
            return pd.to_datetime(s0, dayfirst=True).date()
        except Exception:
            # final fallback: compact letters/digits and attempt to extract day, monthtext, year
            compact = re.sub(r'[^0-9a-zA-Z]', '', low)
            m = re.match(r'(\d{1,2})([A-Za-z]+)(\d{4})', compact)
            if m:
                day, mtext, year = m.groups()
                mm = month_map.get(mtext, month_map.get(mtext.lower()))
                if mm:
                    try:
                        return datetime.strptime(f"{day}.{mm}.{year}", "%d.%m.%Y").date()
                    except Exception:
                        pass
            raise ValueError(f"Unknown datetime string format, unable to parse: {s0}")

    hist_df['per'] = hist_df['per'].apply(_parse_date_str)
    hist_df['NAV'] = pd.to_numeric(hist_df['NAV'], errors='coerce')

    # Requirement step 4c: drop rows before request_start_date
    if request_start is not None:
        hist_df = hist_df[hist_df['per'] >= request_start].copy()

    # 4) extract ausschüttungen
    dis = xls.get("Ausschüttungen")
    if dis is None:
        dis = pd.DataFrame(columns=["Ex-Tag", "Gesamtausschüttung"])
    dis_cols = {c.lower(): c for c in dis.columns}
    if "ex-tag" in dis_cols and "gesamtausschüttung" in dis_cols:
        dis_df = dis[[dis_cols["ex-tag"], dis_cols["gesamtausschüttung"]]].rename(
            columns={dis_cols["ex-tag"]: "Ex-Tag", dis_cols["gesamtausschüttung"]: "Gesamtausschüttung"}
        )
        dis_df = dis_df.dropna(subset=["Ex-Tag"]).copy()
        # parse Ex-Tag using the same helper
        dis_df["Ex-Tag"] = dis_df["Ex-Tag"].apply(_parse_date_str)
        dis_df["Gesamtausschüttung"] = pd.to_numeric(dis_df["Gesamtausschüttung"], errors="coerce")

        # Requirement step 4c: drop rows where Ex-Tag <= request_start_date
        if request_start is not None:
            dis_df = dis_df[dis_df["Ex-Tag"] > request_start].copy()
    else:
        dis_df = pd.DataFrame(columns=["Ex-Tag", "Gesamtausschüttung"])

    # 5) currency check - look at first non-null currency in historisch
    sheet_currency = hist_df["Währung"].dropna().astype(str).str.strip().iloc[0] if not hist_df["Währung"].dropna().empty else None
    if sheet_currency and sheet_currency.upper() != (price_currency or "").upper():
        print(f"Currency mismatch for {isin} ({ticker}): sheet={sheet_currency} vs expected={price_currency}. Skipping.")
        return {"skipped": True, "reason": "currency_mismatch"}

    # 6) Build base price DataFrame
    prices = hist_df[["per", "NAV"]].dropna(subset=["NAV"]).copy()
    prices = prices.rename(columns={"per": "price_date", "NAV": "price_close"})
    prices["dividend_cash"] = 0.0
    raw_fetched = len(prices.index)

    # Map dividends onto price dates
    if not dis_df.empty:
        divs = dis_df.rename(columns={"Ex-Tag": "price_date", "Gesamtausschüttung": "dividend_cash"})
        divs = divs.groupby("price_date").sum().reset_index()
        prices = prices.merge(divs, on="price_date", how="left", suffixes=("", "_d"))
        prices["dividend_cash"] = prices["dividend_cash_d"].fillna(prices["dividend_cash"]).fillna(0.0)
        prices = prices.drop(columns=[c for c in prices.columns if c.endswith("_d")])

    if prices.empty:
        print(f"No NAV rows for {ticker}")
        return empty_provider_result(raw_fetched=raw_fetched)

    # Build canonical records and delegate gap-fill/reconciliation to shared helpers.
    records = []
    for _, row in prices.iterrows():
        price_date = row["price_date"]
        records.append({
            "isin": isin,
            "price_date": price_date.isoformat(),
            "price_close": normalize_float(row["price_close"], decimals=10),
            "dividend_cash": normalize_float(row.get("dividend_cash"), decimals=10) or 0.0,
            "price_date_original": price_date.isoformat(),
            "split_factor": 1.0,
        })

    parsed = len(records)
    if parsed == 0:
        return empty_provider_result(raw_fetched=raw_fetched)

    upsert_records, recon_summary = reconcile_asset_price_data(
        isin=isin,
        asset_start_date=asset_start,
        request_start_date=request_start,
        canonical_rows=records,
        key_fields=["isin", "price_date"],
        compare_fields=["price_close", "price_date_original", "dividend_cash", "split_factor"],
        normalizers={
            "price_date": normalize_date,
            "price_date_original": normalize_date,
            "price_close": lambda v: normalize_float(v, decimals=10),
            "dividend_cash": lambda v: normalize_float(v, decimals=10),
            "split_factor": lambda v: normalize_float(v, decimals=10),
        },
    )

    return persist_price_records(
        isin=isin,
        records=upsert_records,
        dry_run=dry_run,
        recon_summary=recon_summary,
        parsed=parsed,
        raw_fetched=raw_fetched,
    )


def process_all_ishares_assets(dry_run: bool = False):
    """Process all iShares assets using the generic batch processor."""
    return process_provider_batch("ISH", import_ishares_history_for_ticker, dry_run)
