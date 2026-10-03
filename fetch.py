#!/usr/bin/env python3
"""Step 1/3 — download data to data/ (no calculations):
  prices_close.csv   adjusted daily closes for every ticker on the page (Yahoo Finance via yfinance)
  holdings.csv       top HOLDINGS_N holdings of every US-sector-table ETF (official SSGA xlsx where available,
                     else stockanalysis.com); calc.py decides which sectors qualify
  holding_prices.csv adjusted daily closes for those holdings
  fetch_meta.json    timestamps, per-ticker coverage, errors (shown on the page)"""
from common import *
import requests, yfinance as yf

META = {"fetched_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "errors": [], "holdings_errors": {}, "tickers": {}}

def holdings(etf, n=HOLDINGS_N):
    if etf in SSGA:
        try:
            url = f"https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/holdings-daily-us-en-{etf.lower()}.xlsx"
            r = requests.get(url, headers=UA, timeout=30); r.raise_for_status()
            raw = pd.read_excel(io.BytesIO(r.content), header=None)
            asof = str(raw.iloc[2, 1]).replace("As of ", "").strip()
            hdr = raw.index[raw.iloc[:, 0].astype(str).str.strip() == "Name"][0]
            df = pd.read_excel(io.BytesIO(r.content), header=hdr).dropna(subset=["Ticker"])
            df = df[df["Ticker"].astype(str).str.match(r"^[A-Z][A-Z.\-]*$")].sort_values("Weight", ascending=False).head(n)
            return [(str(t).replace(".", "-"), float(w)) for t, w in zip(df.Ticker, df.Weight)], "ssga", asof
        except Exception as e:
            log(f"SSGA holdings {etf} failed ({e!r}); falling back to stockanalysis.com")
    r = requests.get(f"https://stockanalysis.com/etf/{etf.lower()}/holdings/", headers=UA, timeout=30); r.raise_for_status()
    df = pd.read_html(io.StringIO(r.text))[0]
    df = df[df["Symbol"].astype(str).str.match(r"^[A-Z][A-Z.\-]*$")].head(n)
    w = df["% Weight"].astype(str).str.rstrip("%").astype(float)
    return [(str(t).replace(".", "-"), float(x)) for t, x in zip(df.Symbol, w)], "stockanalysis", str(dt.date.today())

if __name__ == "__main__":
    d = yf.download(ALL_TICKERS, period=PRICE_PERIOD, auto_adjust=True, progress=False, threads=True)["Close"]
    for t in ALL_TICKERS:
        s = d[t].dropna() if t in d else pd.Series(dtype=float)
        if s.empty: META["errors"].append(t); log(f"FETCH ERROR: {t} no data")
        else: META["tickers"][t] = {"first": str(s.index[0].date()), "last": str(s.index[-1].date()), "rows": int(len(s))}
    d.to_csv(dpath("prices_close.csv"))
    try: META["currency"] = {"NGSP.L": yf.Ticker("NGSP.L").fast_info.get("currency")}
    except Exception: META["currency"] = {}
    log(f"Prices: {len(META['tickers'])}/{len(ALL_TICKERS)} tickers with data")

    rows = []
    for etf in SECTOR_UNIVERSE:
        try:
            h, src, asof = holdings(etf)
            rows += [{"etf": etf, "ticker": t, "weight": w, "source": src, "source_date": asof} for t, w in h]
            log(f"Holdings {etf}: {len(h)} ({src}, {asof})")
        except Exception as e:
            META["holdings_errors"][etf] = repr(e); log(f"HOLDINGS ERROR {etf}: {e!r}")
    hd = pd.DataFrame(rows, columns=["etf", "ticker", "weight", "source", "source_date"])
    hd.to_csv(dpath("holdings.csv"), index=False)
    if len(hd):
        hp = yf.download(sorted(hd.ticker.unique()), period="1y", auto_adjust=True, progress=False, threads=True)["Close"]
        hp.to_csv(dpath("holding_prices.csv"))
        META["holding_price_missing"] = [t for t in hd.ticker.unique() if t not in hp or hp[t].dropna().empty]
        if META["holding_price_missing"]: log(f"Holding prices missing: {META['holding_price_missing']}")
    json.dump(META, open(dpath("fetch_meta.json"), "w"), indent=2)
    save_log("fetch")
