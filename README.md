# app_check

ASO 查詢面板 v1（純 Python HTTP Server）

## 功能
- 輸入 Android App ID 與 iOS Apple ID
- 選擇地區（TW / US）
- 每行輸入一個關鍵字，查詢 Android / iOS 排名
- 自動保存每次查詢結果到 SQLite（`aso_history.db`）
- 在首頁顯示最近 10 筆歷史紀錄

## 啟動
```bash
python -m venv .venv
source .venv/bin/activate
python app.py
```

開啟 `http://localhost:5000`。
