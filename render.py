#!/usr/bin/env python3
"""Step 3/3 — write table.html (Traditional Chinese, HK) purely from calc.py outputs (summary.json, metrics.csv,
roc_<N>.csv, roc_lastdate.csv). No numbers are typed here."""
from common import *
import re
from html import escape as esc

STATUS = {"Leader": "領先", "Old leader": "舊領先", "Laggard": "落後", "Contradictory": "矛盾"}
NOTE = {"3M beats benchmark but 1M has turned worse": "3個月跑贏基準，但1個月已經轉弱",
        "1M beats benchmark but 3M lags (early turn, unconfirmed)": "1個月跑贏但3個月仍落後（初步轉勢，未確認）",
        "RS 1M&3M positive but not above a rising 20/50DMA": "1個月及3個月相對強度皆正，但未企穩向上嘅20日／50日線",
        "RS 1M&3M negative but trend not down (above rising MA)": "1個月及3個月相對強度皆負，但走勢未轉跌"}
WD = "一二三四五六日"
FONT = "'PingFang HK','Noto Sans CJK TC','Noto Sans TC','Microsoft JhengHei','微軟正黑體','PMingLiU','新細明體',sans-serif"

def cn(t): return CN_NAMES.get(t, "（未有中文名）")
def cdate(d): d = pd.Timestamp(d); return f"{d.year}年{d.month}月{d.day}日"
def cts(s):
    m_ = re.match(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}:\d{2})", str(s or ""))
    return f"{m_.group(1)}年{int(m_.group(2))}月{int(m_.group(3))}日 {m_.group(4)}（香港／台北時間）" if m_ else "無數據"
def f(x, d=1, pct=True):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "無數據"
    return (f"{x:+.{d}f}" if pct else f"{x:,.{d}f}") + ("%" if pct else "")
def cls(x): return "pos" if isinstance(x, (int, float)) and x > 0 else "neg" if isinstance(x, (int, float)) and x < 0 else ""
def arrow(b): return "<span class=pos>▲</span>" if b else "<span class=neg>▼</span>"
def mlabel(N): return f"約{round(N / 21)}個月"
HDR6 = "<th>1個月回報</th><th>3個月回報</th><th>1個月相對強度</th><th>3個月相對強度</th><th>距20日線（方向）</th><th>距50日線（方向）</th>"
def cells6(r):
    return (f"<td class={cls(r.ret_1m)}>{f(r.ret_1m)}</td><td class={cls(r.ret_3m)}>{f(r.ret_3m)}</td>"
            f"<td class={cls(r.rs_1m)}>{f(r.rs_1m)}</td><td class={cls(r.rs_3m)}>{f(r.rs_3m)}</td>"
            f"<td class={cls(r.vs20dma_pct)}>{f(r.vs20dma_pct)} {arrow(r.dma20_rising)}</td><td class={cls(r.vs50dma_pct)}>{f(r.vs50dma_pct)} {arrow(r.dma50_rising)}</td>")

def section_drill(S, m, dd):
    h = [f"<h2>二、成份股分析：只限合格板塊（每隻基金頭 {HOLDINGS_N} 大持倉，相對 SPY 強度，50日線同方向）</h2>"]
    P = S.get("passing", [])
    others = [t for t in SECTOR_UNIVERSE if t not in P and t in m.index]
    h.append("<div class=note>合格條件（沿用之前嘅領先規則）：1個月及3個月相對 SPY 強度皆正，兼收市企喺向上嘅20日線或50日線之上；舊領先剔除。"
             f"範圍＝上面美股板塊表除 SPY 外全部代號。最強＝相對 SPY 強度（1個月同3個月平均）最高，而且收市企喺向上嘅50日線之上，每隻基金取頭3隻。"
             f"1個月＝{N1M}個交易日，3個月＝{N3M}個交易日；50日線向上＝同{SLOPE50}個交易日前比較。</div>")
    if not P:
        h.append("<p class=note>今期冇板塊合格，所以冇成份股分析。</p>")
    hdr = "<tr><th>名次</th><th class=l>代號</th><th>基金內比重（%）</th><th>1個月相對強度</th><th>3個月相對強度</th><th>距50日線（方向）</th></tr>"
    for etf in P:
        r = m.loc[etf]; info = S.get("drill_info", {}).get(etf)
        h.append(f"<h3 class=sub>{etf} {cn(etf)}　<span class=note>（基金本身：1個月相對強度 {f(r.rs_1m)}，3個月相對強度 {f(r.rs_3m)}，距20日線 {f(r.vs20dma_pct)} {arrow(r.dma20_rising)}，距50日線 {f(r.vs50dma_pct)} {arrow(r.dma50_rising)}）</span></h3>")
        if not isinstance(info, dict):
            err = S.get("holdings_errors", {}).get(etf)
            h.append(f"<p class=neg>未能取得 {etf} 嘅持倉數據{'（下載失敗）' if err else ''}，所以冇成份股分析。</p>"); continue
        sub = dd[dd.etf == etf].sort_values("rank")
        h.append("<table class=drill>" + hdr)
        for _, x in sub.iterrows():
            h.append(f"<tr><td>{int(x['rank'])}</td><td class=l><b>{x.ticker}</b></td><td>{x.weight:.2f}</td><td class={cls(x.rs_1m)}>{f(x.rs_1m)}</td>"
                     f"<td class={cls(x.rs_3m)}>{f(x.rs_3m)}</td><td class={cls(x.vs50dma_pct)}>{f(x.vs50dma_pct)} {arrow(x.dma50_rising)}</td></tr>")
        if len(sub) < 3:
            h.append(f"<tr><td colspan=6 class=l style='text-align:left'>只有 {len(sub)} 隻持倉符合「企喺向上嘅50日線之上」。</td></tr>")
        h.append("</table>")
        src = (f"道富環球投資（SSGA）官方每日持倉檔（截至{cdate(pd.Timestamp(info['source_date']))}）" if info["source"] == "ssga"
               else f"stockanalysis.com 網站（{cdate(info['source_date'])}讀取；發行商官方檔案未能自動下載）")
        sk = f"；以下持倉冇足夠價格數據，已略過：{'、'.join(info['skipped'])}" if info["skipped"] else ""
        h.append(f"<div class=note>持倉來源：{src}；頭 {info['n_holdings']} 大持倉之中 {info['n_priced']} 隻有價格數據{sk}。</div>")
    if others:
        def why(t):
            st = m.loc[t].status
            return {"Old leader": "舊領先", "Laggard": "落後", "Contradictory": "矛盾"}.get(st, "唔合格")
        h.append("<div class=note>唔合格板塊：" + "、".join(f"{t} {cn(t)}（{why(t)}）" for t in others) + "。</div>")
    return "\n".join(h)

def section_roc(S, roc, lastd):
    asof = pd.Timestamp(S["asof"])
    h = ["<h2>一、變動率動量排名（每週快照，仿照參考試算表格式）</h2>",
         "<div class=note>選擇變動率回望期：" + " ".join(
             f"<button class=rocbtn data-n={N} onclick=\"showRoc({N})\">{N}日（{mlabel(N)}{'，預設' if N == ROC_DEFAULT else ''}）</button>" for N in ROC_PERIODS) +
         "　參考試算表冇註明用幾多日計算，用雅虎財經數據亦對唔返，所以預設用63日，可自行切換。</div>"]
    stale = {t: d for t, d in lastd.items() if d and pd.Timestamp(d) < asof}
    for N in ROC_PERIODS:
        if N not in roc: h.append(f"<p class=neg>{N}日變動率數據缺失。</p>"); continue
        df = roc[N]; dates = list(df.columns)
        h.append(f"<div class=rocpanel id=roc{N} style='display:{'block' if N == ROC_DEFAULT else 'none'}'>")
        h.append(f"<div class=refhdr>日期：{cdate(asof)}<br>變動率＝每個星期五收市價相對 {N} 個美股交易日前嘅變幅（%）</div>")
        for key, title, tks in ROC_SHEETS:
            sub = df.reindex(tks)
            have = sub[sub[dates[0]].notna()].sort_values(dates[0], ascending=False)
            miss = sub[sub[dates[0]].isna()]
            sub = pd.concat([have, miss])
            prev = sub.drop(index=BENCH, errors="ignore")[dates[1]].rank(ascending=False)
            h.append(f"<div class=refsubj>主題：{title}</div><table class=roc><tr><th>排名</th><th>週變化</th><th class=l>代號</th><th class=l>名稱</th>"
                     + "".join(f"<th>變動率<br>{pd.Timestamp(d).month}月{pd.Timestamp(d).day}日</th>" for d in dates) + "</tr>")
            rank = 0
            for t, r in sub.iterrows():
                is_b = t == BENCH; vals = r.values.astype(float)
                if not is_b and not np.isnan(vals[0]): rank += 1
                pr = prev.get(t)
                dlt = None if (is_b or np.isnan(vals[0]) or pd.isna(pr)) else int(pr) - rank
                dtxt = "" if dlt is None else ("<span class=pos>▲%d</span>" % dlt if dlt > 0 else "<span class=neg>▼%d</span>" % -dlt if dlt < 0 else "＝")
                cs = []
                for j, v in enumerate(vals):
                    c = ""
                    if j == 0 and not np.isnan(v) and np.isfinite(vals).sum() > 1:
                        if v >= np.nanmax(vals): c = " class=rmax"
                        elif v <= np.nanmin(vals): c = " class=rmin"
                    cs.append(f"<td{c}>{'無數據' if np.isnan(v) else f'{v:.3f}'}</td>")
                mark = "＊" if t in stale else ""
                rk = "" if is_b else (rank if not np.isnan(vals[0]) else "—")
                h.append(f"<tr{' class=bench' if is_b else ''}><td>{rk}</td><td>{dtxt}</td><td class=l>{t}{mark}</td><td class=l>{cn(t)}</td>{''.join(cs)}</tr>")
            h.append("</table>")
        h.append("</div>")
    notes = []
    for t, d in stale.items(): notes.append(f"＊{t}：最新一欄用 {cdate(d)} 收市價（{cdate(asof)} 當日未有數據）。")
    if "NGSP.L" in lastd:
        ccy = S.get("currency", {}).get("NGSP.L")
        notes.append(f"NGSP.L 喺倫敦交易所上市{'（以便士計價）' if ccy == 'GBp' else ''}；變動率係百分比，唔受貨幣影響。倫敦假期或者美股開市但倫敦休市嘅日子，用之前最近一個收市價。")
    notes.append("加密貨幣七日都交易：每個星期五用雅虎財經當日（世界協調時間）日線收市價，回望期用美股交易日計算，所以同股票基金嘅回望期一致。")
    h.append("<div class=note>" + "".join(f"<div>{x}</div>" for x in notes) +
             "<div>格式跟參考試算表：最新一週排最左，按最新變動率由高至低排列；黃色行係 SPY 基準，照排位插入但唔計排名。"
             "最新一格 <span class=rmax>&nbsp;紅字粉紅底&nbsp;</span>＝十週內最高；<span class=rmin>&nbsp;藍字淺藍底&nbsp;</span>＝十週內最低。"
             "週變化＝同上一個星期五比較嘅排名升跌。價格來源：雅虎財經經調整每日收市價（已計派息）。</div></div>")
    h.append("""<script>function showRoc(n){document.querySelectorAll('.rocpanel').forEach(e=>e.style.display=(e.id=='roc'+n)?'block':'none');
document.querySelectorAll('.rocbtn').forEach(b=>b.classList.toggle('on',b.dataset.n==n));}showRoc(%d);</script>""" % ROC_DEFAULT)
    return "\n".join(h)

def main():
    S = json.load(open(opath("summary.json")))
    m = pd.read_csv(opath("metrics.csv"), index_col=0)
    for c in ("dma20_rising", "dma50_rising"): m[c] = m[c].astype(bool)
    roc = {}
    for N in ROC_PERIODS:
        if os.path.exists(opath(f"roc_{N}.csv")): roc[N] = pd.read_csv(opath(f"roc_{N}.csv"), index_col=0)
    lastd = pd.read_csv(opath("roc_lastdate.csv"), index_col=0).iloc[:, 0].dropna().to_dict() if os.path.exists(opath("roc_lastdate.csv")) else {}
    asof = pd.Timestamp(S["asof"])
    h = [f"""<!doctype html><html lang="zh-Hant-HK"><head><meta charset=utf-8><title>美股動量排名及成份股分析 {cdate(asof)}</title><style>
body{{font:13px/1.5 {FONT};max-width:1150px;margin:16px auto;color:#222;padding:0 12px}}
h1{{font-size:20px;margin:0}} h2{{font-size:15px;margin:22px 0 6px;border-bottom:2px solid #333;padding-bottom:3px}}
table{{border-collapse:collapse;width:100%;margin:4px 0}} th,td{{border:1px solid #ccc;padding:4px 6px;text-align:right}}
th{{background:#f2f2f2}} td.l,th.l{{text-align:left}} .pos{{color:#0a7d2c}} .neg{{color:#c0392b}} .note{{color:#666;font-size:12px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} .cell{{border:1px solid #bbb;border-radius:6px;padding:8px}} .cell h3{{margin:0 0 4px;font-size:14px}} h3.sub{{font-size:13px;margin:12px 0 2px}} table.drill{{width:auto;min-width:560px}}
table.roc td,table.roc th{{font-family:'PMingLiU','新細明體',{FONT};font-size:12px;padding:3px 5px}}
tr.bench td{{background:#FFFF00}} .rmax{{color:#FF0000;background:#FF9999}} .rmin{{color:#4472C4;background:#B4C6E7}}
.refhdr{{margin:6px 0;font-family:'PMingLiU','新細明體',{FONT}}} .refsubj{{margin:12px 0 2px;font-weight:bold}}
.rocbtn{{margin:2px;padding:2px 8px;border:1px solid #888;background:#fff;cursor:pointer;font-family:{FONT}}} .rocbtn.on{{background:#333;color:#fff}}
</style></head><body><h1>美股動量排名及成份股分析</h1>
<div class=note>收市價截至 <b>{cdate(asof)}</b>（美國時間星期{WD[asof.weekday()]}）。頁面生成 {cts(S['run'])}；數據下載 {cts(S.get('fetched_at'))}。</div>"""]
    if S.get("holdings_errors"):
        h.append("<p class=neg><b>持倉下載失敗：</b>" + "、".join(esc(t) for t in S["holdings_errors"]) + "，相關板塊冇成份股分析。</p>")
    if S.get("fetch_errors"):
        h.append("<p class=neg><b>下載失敗：</b>" + "、".join(esc(t) for t in S["fetch_errors"]) + "，相關數字顯示為「無數據」，冇用任何替代數字。</p>")
    dd = pd.read_csv(opath("drilldown.csv")) if os.path.exists(opath("drilldown.csv")) else pd.DataFrame(columns=["etf", "rank"])
    if "dma50_rising" in dd: dd["dma50_rising"] = dd["dma50_rising"].astype(bool)
    h.append(section_roc(S, roc, lastd))
    h.append(section_drill(S, m, dd))
    h.append("</body></html>")
    open(opath("table.html"), "w").write("\n".join(h))
    print("已輸出", opath("table.html"))

if __name__ == "__main__":
    main()
