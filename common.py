"""Shared config + helpers (fetch.py -> calc.py -> render.py). Page = equity themes (section 2) + ROC momentum ranking."""
import io, os, sys, json, datetime as dt, traceback, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data"); OUT = ROOT; LOGS = os.path.join(ROOT, "logs")
for _d in (DATA, LOGS): os.makedirs(_d, exist_ok=True)
LOG = []
def log(msg): print(msg); LOG.append(msg)
def save_log(name): open(os.path.join(LOGS, f"{name}.log"), "w").write("\n".join(LOG))
def dpath(*p): return os.path.join(DATA, *p)
def opath(*p): return os.path.join(OUT, *p)

BENCH = "SPY"
HOLDINGS_N = 25
SSGA = {"XLK", "XLF", "XLE", "XLB", "XLV", "XLP", "XLU", "XLC", "XLI", "XLY"}   # official issuer xlsx available
N1M, N3M = 21, 63
SLOPE20, SLOPE50 = 5, 10   # rising = MA today > MA N sessions ago
PRICE_PERIOD = "2y"

# ROC momentum-ranking sheets (layout of the user's reference workbook); every sheet carries a SPY benchmark row
ROC_SHEETS = [
    ("sector", "美股板塊ETF動量排名", ["SMH", "XLK", "IGV", "QQQ", "XLE", "XLV", "SPY", "XLC", "XLF", "XLI", "XLP", "XLB", "XLY", "VNQ", "XLU"]),
    ("commodity", "商品ETF動量排名", ["DBE", "USO", "CANE", "SOYB", "CORN", "WEAT", "SPY", "DBA", "GLD", "SLV", "NGSP.L", "BWET", "CRAK"]),
    ("bond", "債券ETF動量排名", ["SPY", "BKLN", "BIL", "SHY", "IEI", "AGG", "IEF", "TLH", "TLT", "LTPZ"]),
    ("crypto", "加密貨幣動量排名", ["ETH-USD", "BTC-USD", "SPY"]),
]
ROC_PERIODS = (21, 63, 126)
ROC_DEFAULT = 63
N_WEEKS = 10
ALIGN_TOL_DAYS = 7          # max staleness when aligning a series to SPY's calendar

ALL_TICKERS = sorted(set([BENCH] + [t for _, _, ts in ROC_SHEETS for t in ts]))
# qualification universe for the holdings drill-down = every non-SPY row of the US sector ranking table
SECTOR_UNIVERSE = [t for t in ROC_SHEETS[0][2] if t != BENCH]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

CN_NAMES = {
    "SPY": "標普500", "QQQ": "納指100", "SMH": "半導體", "XLK": "科技", "IGV": "軟件", "XLE": "能源", "XLV": "醫療保健",
    "XLC": "通訊服務", "XLF": "金融", "XLI": "工業", "XLP": "必需消費", "XLB": "原材料", "XLY": "非必需消費",
    "VNQ": "房地產信託", "XLU": "公用事業",
    "DBE": "能源商品", "USO": "原油", "CANE": "糖", "SOYB": "大豆", "CORN": "粟米", "WEAT": "小麥", "DBA": "農產品",
    "GLD": "黃金", "SLV": "白銀", "NGSP.L": "天然氣（倫敦上市，英鎊計價）", "BWET": "油輪運費", "CRAK": "煉油商",
    "BKLN": "優先級貸款", "BIL": "1至3個月美國國庫券", "SHY": "1至3年美國國債", "IEI": "3至7年美國國債",
    "AGG": "美國綜合債券", "IEF": "7至10年美國國債", "TLH": "10至20年美國國債", "TLT": "20年以上美國國債",
    "LTPZ": "15年以上美國抗通脹國債", "ETH-USD": "以太幣兌美元", "BTC-USD": "比特幣兌美元"}

def ret(s, n):
    s = s.dropna()
    return (s.iloc[-1] / s.iloc[-1 - n] - 1) * 100 if len(s) > n else np.nan

def ma_stats(s):
    s = s.dropna(); r = {}
    for n, lag in ((20, SLOPE20), (50, SLOPE50)):
        ma = s.rolling(n).mean()
        r[f"dma{n}"] = ma.iloc[-1]
        r[f"vs{n}dma_pct"] = (s.iloc[-1] / ma.iloc[-1] - 1) * 100
        r[f"dma{n}_rising"] = bool(ma.iloc[-1] > ma.iloc[-1 - lag])
        r[f"dma{n}_slope_pct"] = (ma.iloc[-1] / ma.iloc[-1 - lag] - 1) * 100
    return r
