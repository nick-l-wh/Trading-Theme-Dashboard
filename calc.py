#!/usr/bin/env python3
"""Step 2/3 — read data/ only (no network). Computes (a) weekly ROC momentum ranking on SPY's trading calendar and
(b) sector qualification (Leader rule vs SPY: RS 1M & 3M > 0 and close above a rising 20DMA or 50DMA; old leaders
excluded) plus top-3 strongest holdings (highest avg RS vs SPY, close above rising 50DMA) per qualifying sector.
Writes roc_<N>.csv, roc_lastdate.csv, metrics.csv, drilldown.csv, summary.json."""
from common import *

META = json.load(open(dpath("fetch_meta.json"))) if os.path.exists(dpath("fetch_meta.json")) else {}

def classify(r):   # equity version of the original rules (benchmark SPY)
    up = (r.vs20dma_pct > 0 and r.dma20_rising) or (r.vs50dma_pct > 0 and r.dma50_rising)
    dn = (r.vs20dma_pct < 0 and not r.dma20_rising) or (r.vs50dma_pct < 0 and not r.dma50_rising)
    if r.rs_1m > 0 and r.rs_3m > 0:
        return ("Leader", "") if up else ("Contradictory", "RS 1M&3M positive but not above a rising 20/50DMA")
    if r.rs_3m > 0 and r.rs_1m <= 0: return "Old leader", "3M beats benchmark but 1M has turned worse"
    if r.rs_1m < 0 and r.rs_3m < 0:
        return ("Laggard", "") if (dn and not up) else ("Contradictory", "RS 1M&3M negative but trend not down (above rising MA)")
    return "Contradictory", "1M beats benchmark but 3M lags (early turn, unconfirmed)"

def sector_section(px):
    """Qualify sectors (Leader rule vs SPY) over SECTOR_UNIVERSE, then top-3 strongest holdings per qualifying ETF."""
    rows = []
    for t in [BENCH] + SECTOR_UNIVERSE:
        s = px[t].dropna() if t in px else pd.Series(dtype=float)
        if len(s) < 70: log(f"DATA GAP: {t} insufficient history"); continue
        r = {"ticker": t, "close": s.iloc[-1], "ret_1m": ret(s, N1M), "ret_3m": ret(s, N3M)}
        r.update(ma_stats(s)); rows.append(r)
    m = pd.DataFrame(rows).set_index("ticker")
    for t in m.index.drop(BENCH):
        m.loc[t, "rs_1m"] = m.loc[t, "ret_1m"] - m.loc[BENCH, "ret_1m"]
        m.loc[t, "rs_3m"] = m.loc[t, "ret_3m"] - m.loc[BENCH, "ret_3m"]
        c, why = classify(m.loc[t]); m.loc[t, "status"] = c; m.loc[t, "status_note"] = why
        m.loc[t, "score"] = (m.loc[t, "rs_1m"] + m.loc[t, "rs_3m"]) / 2
    m.round(6).to_csv(opath("metrics.csv"))
    passing = list(m[m.status == "Leader"].sort_values("score", ascending=False).index)
    log(f"Qualifying sectors: {passing}")
    # drill-down
    out, errs = [], {}
    hd = pd.read_csv(dpath("holdings.csv")) if os.path.exists(dpath("holdings.csv")) else pd.DataFrame(columns=["etf"])
    hp = pd.read_csv(dpath("holding_prices.csv"), index_col=0, parse_dates=True).sort_index() if os.path.exists(dpath("holding_prices.csv")) else pd.DataFrame()
    spy1, spy3 = m.loc[BENCH, "ret_1m"], m.loc[BENCH, "ret_3m"]
    for etf in passing:
        h = hd[hd.etf == etf]
        if h.empty: errs[etf] = "no_holdings"; log(f"DRILL GAP {etf}: no holdings in cache"); continue
        recs, skipped = [], []
        for t, w in zip(h.ticker, h.weight):
            if t not in hp or hp[t].dropna().shape[0] < 70: skipped.append(t); continue
            s = hp[t].dropna(); st = ma_stats(s)
            rs1, rs3 = ret(s, N1M) - spy1, ret(s, N3M) - spy3
            recs.append({"etf": etf, "ticker": t, "weight": w, "rs_1m": rs1, "rs_3m": rs3, "rs_avg": (rs1 + rs3) / 2,
                         "vs50dma_pct": st["vs50dma_pct"], "dma50": st["dma50"], "dma50_rising": st["dma50_rising"]})
        df = pd.DataFrame(recs)
        top = df[(df.vs50dma_pct > 0) & df.dma50_rising].sort_values("rs_avg", ascending=False).head(3) if len(df) else df
        for i, r in enumerate(top.to_dict("records"), 1): out.append(dict(r, rank=i))
        info = {"n_holdings": int(len(h)), "n_priced": int(len(df)), "skipped": skipped,
                "source": h.source.iloc[0], "source_date": str(h.source_date.iloc[0]), "n_top": int(len(top))}
        errs[etf] = info
        log(f"Drill-down {etf}: {len(df)}/{len(h)} priced; top3={list(top.ticker)}; skipped={skipped}")
    pd.DataFrame(out, columns=["etf","rank","ticker","weight","rs_1m","rs_3m","rs_avg","vs50dma_pct","dma50","dma50_rising"]).to_csv(opath("drilldown.csv"), index=False)
    return {"passing": passing, "old_leaders": list(m[m.status == "Old leader"].index), "drill_info": errs}

def roc_section(px):
    spy_idx = px[BENCH].dropna().index
    fridays = [f for f in pd.date_range(end=spy_idx[-1], periods=N_WEEKS * 2, freq="W-FRI") if f <= spy_idx[-1]][-N_WEEKS:][::-1]
    snap = [spy_idx[spy_idx <= f][-1] for f in fridays]          # last SPY trading day on/before each Friday
    tick = sorted({t for _, _, ts in ROC_SHEETS for t in ts})
    aligned, lastdate = {}, {}
    for t in tick:
        s = px[t].dropna() if t in px else pd.Series(dtype=float)
        if s.empty: log(f"DATA GAP: {t} no prices"); continue
        # value on each SPY date = last own close on/before it (handles LSE holidays, crypto weekends)
        aligned[t] = s.reindex(spy_idx, method="ffill", tolerance=pd.Timedelta(days=ALIGN_TOL_DAYS))
        lastdate[t] = str(s[s.index <= snap[0] + pd.Timedelta(hours=23)].index[-1].date()) if (s.index <= snap[0] + pd.Timedelta(hours=23)).any() else None
    A = pd.DataFrame(aligned)
    for N in ROC_PERIODS:
        roc = (A / A.shift(N) - 1) * 100
        df = roc.loc[snap].T; df.columns = [str(d.date()) for d in snap]
        df = df.reindex(tick)
        df.to_csv(opath(f"roc_{N}.csv"))
        for t in df.index[df.iloc[:, 0].isna()]: log(f"ROC GAP: {t} ROC{N} newest week n/a (history too short or no data)")
    pd.Series(lastdate, name="last_close_used").to_csv(opath("roc_lastdate.csv"))
    log(f"ROC ranking: weekly snapshots {snap[-1].date()} .. {snap[0].date()} (SPY calendar)")
    return [str(d.date()) for d in snap]

if __name__ == "__main__":
    for f_ in ["metrics.csv", "summary.json", "roc_lastdate.csv", "drilldown.csv"] + [f"roc_{N}.csv" for N in ROC_PERIODS]:
        if os.path.exists(opath(f_)): os.remove(opath(f_))
    px = pd.read_csv(dpath("prices_close.csv"), index_col=0, parse_dates=True).sort_index()
    if BENCH not in px or px[BENCH].dropna().empty: sys.exit("SPY prices missing — cannot compute")
    asof = px[BENCH].dropna().index[-1].date()
    log(f"Price data as of {asof}")
    for t in META.get("errors", []): log(f"FETCH ERROR (from fetch.py): {t}")
    S = {"asof": str(asof), "run": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "fetched_at": META.get("fetched_at"),
         "fetch_errors": META.get("errors", []), "holdings_errors": META.get("holdings_errors", {}), "currency": META.get("currency", {})}
    S.update(sector_section(px))
    S["snapshots"] = roc_section(px)
    json.dump(S, open(opath("summary.json"), "w"), indent=2, default=str)
    save_log("calc")
    print(json.dumps({k: S[k] for k in ("asof", "passing", "old_leaders")}, default=str))
