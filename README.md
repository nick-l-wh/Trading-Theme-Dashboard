# Trading-Theme Dashboard 交易主題儀表板

用 Yahoo 數據自動計算美股板塊、商品、債券、加密貨幣嘅變動率動量排名（全部對比 SPY），並列出合格板塊嘅最強三隻成份股。

## 運行
```
python -m venv .venv && .venv/bin/pip install -r requirements.txt
./run_all.sh
```
次序：`fetch.py`（下載數據到 `data/`）→ `calc.py`（計算排名同合格板塊）→ `render.py`（生成 `table.html`）。

代號同中文名喺 `common.py` 修改。
