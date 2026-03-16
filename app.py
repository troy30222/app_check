from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import streamlit as st

try:
    from google_play_scraper import search as gp_search
except Exception:
    gp_search = None

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "aso_history.db"

import html
import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "aso_history.db")
HOST = "0.0.0.0"
PORT = 5000

DEFAULT_KEYWORDS = [
    "vision",
    "vision fitness",
    "vision 健身",
    "vision喬山",
    "johnson fitness",
    "matrix fitness",
    "horizon fitness",
    "johnson health tech",
    "jht fitness",
    "跑步機 app",
    "飛輪 app",
    "運動追蹤",
    "健身紀錄",
    "居家健身",
    "home workout",
    "虛擬跑步",
    "virtual run",
    "training plan",
    "心率監控",
    "apple health sync",
    "google fit connect",
    "健身數據",
    "technogym",
    "kinomap",
    "zwift",
    "peloton",
    "ifit",
]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            country TEXT NOT NULL,
            android_app_id TEXT NOT NULL,
            ios_app_id TEXT NOT NULL,
            keywords_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            keyword TEXT NOT NULL,
            rank_text TEXT NOT NULL,
            FOREIGN KEY (check_id) REFERENCES checks (id)
        )
        """
    )
    conn.commit()
    conn.close()


def parse_keywords(raw: str) -> list[str]:
    return [x.strip() for x in raw.splitlines() if x.strip()]


def get_google_play_rank(keyword: str, target_package_id: str, country: str = "tw", lang: str = "zh") -> str:
    if gp_search is None:
        return "套件缺失: google-play-scraper"
    try:
        results = gp_search(keyword, lang=lang, country=country, n_hits=100)
        for idx, item in enumerate(results):
            if item.get("appId") == target_package_id:

def fetch_json(url: str, params: dict[str, str]) -> dict:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))


def fetch_text(url: str, params: dict[str, str]) -> str:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as res:
        return res.read().decode("utf-8", errors="ignore")


def get_google_play_rank(keyword: str, target_package_id: str, country: str = "tw", lang: str = "zh-TW") -> str:
    try:
        html_text = fetch_text(
            "https://play.google.com/store/search",
            {"q": keyword, "c": "apps", "hl": lang, "gl": country.upper()},
        )
        app_ids = re.findall(r"/store/apps/details\\?id=([a-zA-Z0-9_\\.]+)", html_text)
        unique = []
        for app_id in app_ids:
            if app_id not in unique:
                unique.append(app_id)
            if len(unique) >= 100:
                break
        for idx, app_id in enumerate(unique):
            if app_id == target_package_id:
                return str(idx + 1)
        return "100+ (未進榜)"
    except Exception as exc:
        return f"錯誤: {exc}"


def get_app_store_rank_by_id(keyword: str, target_apple_id: str, country: str = "tw") -> str:
    url = "https://itunes.apple.com/search"
    params = {"term": keyword, "country": country, "entity": "software", "limit": 100}

    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()

        results = resp.json().get("results", [])

        for idx, item in enumerate(results):
            if str(item.get("trackId")) == str(target_apple_id):
                return str(idx + 1)

        return "100+ (未進榜)"

    except Exception as exc:
        return f"錯誤: {exc}"


def save_check(country: str, android_app_id: str, ios_app_id: str, keywords: list[str], rows: list[dict[str, str]]) -> None:
    conn = get_conn()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        "INSERT INTO checks (created_at, country, android_app_id, ios_app_id, keywords_json) VALUES (?, ?, ?, ?, ?)",
        (created_at, country, android_app_id, ios_app_id, json.dumps(keywords, ensure_ascii=False)),
    )
    check_id = int(cur.lastrowid)

    check_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO rankings (check_id, platform, keyword, rank_text) VALUES (?, ?, ?, ?)",
        [(check_id, r["platform"], r["keyword"], r["rank"]) for r in rows],
    )
    conn.commit()
    conn.close()


def get_recent_checks(limit: int = 10) -> list[dict[str, Any]]:

def get_recent_checks(limit: int = 10) -> list[dict]:
    conn = get_conn()
    checks = conn.execute(
        "SELECT id, created_at, country, android_app_id, ios_app_id FROM checks ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    payload: list[dict[str, Any]] = []

    payload = []
    for c in checks:
        rankings = conn.execute(
            "SELECT platform, keyword, rank_text FROM rankings WHERE check_id = ? ORDER BY platform, keyword",
            (c["id"],),
        ).fetchall()
        payload.append({"check": dict(c), "rankings": [dict(r) for r in rankings]})

        payload.append({"check": dict(c), "rankings": [dict(x) for x in rankings]})
    conn.close()
    return payload


def run_check(android_app_id: str, ios_app_id: str, country: str, keywords: list[str], sleep_sec: float = 0.3) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    progress = st.progress(0, text="開始查詢...")
    total = len(keywords)

    for idx, kw in enumerate(keywords, start=1):
        a_rank = get_google_play_rank(kw, android_app_id, country=country)
        i_rank = get_app_store_rank_by_id(kw, ios_app_id, country=country)
        rows.append({"platform": "Android", "keyword": kw, "rank": a_rank})
        rows.append({"platform": "iOS", "keyword": kw, "rank": i_rank})

        progress.progress(int(idx / total * 100), text=f"查詢中 {idx}/{total}: {kw}")
        time.sleep(sleep_sec)

    progress.progress(100, text="查詢完成")
    return rows


def render_history() -> None:
    st.subheader("歷史紀錄（最近 10 筆）")
    history = get_recent_checks(limit=10)

    if not history:
        st.info("尚無歷史紀錄")
        return

    for item in history:
        c = item["check"]
        with st.expander(
            f"#{c['id']} | {c['created_at']} | {c['country'].upper()} | Android: {c['android_app_id']} | iOS: {c['ios_app_id']}",
            expanded=False,
        ):
            st.dataframe(item["rankings"], use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="ASO 查詢面板 v1", layout="wide")
    init_db()

    st.title("ASO 查詢面板 v1")
    st.caption("可追蹤 Android / iOS 關鍵字排名，支援 TW/US，並保留歷史紀錄供比對。")

    with st.form("aso_form"):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            android_app_id = st.text_input("Android App ID", value="com.johnsonfitness.visionapp")
        with col2:
            ios_app_id = st.text_input("iOS Apple ID", value="6738464990")
        with col3:
            country = st.selectbox("地區", options=["tw", "us"], format_func=lambda x: x.upper())

        keywords_input = st.text_area("關鍵字（每行一個）", value="\n".join(DEFAULT_KEYWORDS), height=220)
        submitted = st.form_submit_button("開始查詢並保存", type="primary")

    if submitted:
        keywords = parse_keywords(keywords_input)
        if not android_app_id.strip() or not ios_app_id.strip() or not keywords:
            st.error("請完整填寫 Android App ID、iOS Apple ID 與關鍵字。")
        else:
            result_rows = run_check(android_app_id.strip(), ios_app_id.strip(), country, keywords)
            save_check(country, android_app_id.strip(), ios_app_id.strip(), keywords, result_rows)
            st.success("查詢完成，已保存紀錄。")
            st.subheader("本次查詢結果")
            st.dataframe(result_rows, use_container_width=True)

    st.divider()
    render_history()


if __name__ == "__main__":
    main()

def render_page(result_rows: list[dict] | None = None, selected_country: str = "tw", android_app_id: str = "com.johnsonfitness.visionapp", ios_app_id: str = "6738464990", keywords_text: str | None = None) -> str:
    if keywords_text is None:
        keywords_text = "\n".join(DEFAULT_KEYWORDS)
    history = get_recent_checks()

    rows_html = ""
    if result_rows:
        body = "".join(
            f"<tr><td>{html.escape(r['platform'])}</td><td>{html.escape(r['keyword'])}</td><td>{html.escape(r['rank'])}</td></tr>"
            for r in result_rows
        )
        rows_html = f"""
        <section class='panel'>
          <h2>本次查詢結果</h2>
          <table><thead><tr><th>平台</th><th>關鍵字</th><th>排名</th></tr></thead><tbody>{body}</tbody></table>
        </section>
        """

    history_html = ""
    if history:
        parts = []
        for item in history:
            c = item["check"]
            rs = "".join(
                f"<tr><td>{html.escape(r['platform'])}</td><td>{html.escape(r['keyword'])}</td><td>{html.escape(r['rank_text'])}</td></tr>"
                for r in item["rankings"]
            )
            parts.append(
                f"<details><summary>#{c['id']} | {c['created_at']} | {c['country'].upper()} | Android: {html.escape(c['android_app_id'])} | iOS: {html.escape(c['ios_app_id'])}</summary><table><thead><tr><th>平台</th><th>關鍵字</th><th>排名</th></tr></thead><tbody>{rs}</tbody></table></details>"
            )
        history_html = "".join(parts)
    else:
        history_html = "<p>尚無歷史紀錄。</p>"

    return f"""<!doctype html>
<html lang='zh-Hant'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>ASO 查詢面板 v1</title><link rel='stylesheet' href='/static/style.css'></head><body>
<main class='container'>
  <h1>ASO 查詢面板 v1</h1>
  <p>輸入 App ID、地區與關鍵字，一次查 Android / iOS 排名並保存歷史紀錄。</p>
  <form method='post' action='/run' class='panel'>
    <label>Android App ID<input name='android_app_id' required value='{html.escape(android_app_id)}'></label>
    <label>iOS Apple ID<input name='ios_app_id' required value='{html.escape(ios_app_id)}'></label>
    <label>地區
      <select name='country'>
        <option value='tw' {'selected' if selected_country == 'tw' else ''}>TW</option>
        <option value='us' {'selected' if selected_country == 'us' else ''}>US</option>
      </select>
    </label>
    <label>關鍵字（每行一個）<textarea name='keywords' rows='10' required>{html.escape(keywords_text)}</textarea></label>
    <button type='submit'>開始查詢並保存</button>
  </form>
  {rows_html}
  <section class='panel'><h2>歷史紀錄（最近 10 筆）</h2>{history_html}</section>
</main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self.respond_html(render_page())
            return
        if self.path == "/static/style.css":
            with open(os.path.join(BASE_DIR, "static", "style.css"), "rb") as f:
                css = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/css; charset=utf-8")
            self.end_headers()
            self.wfile.write(css)
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/run":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        form = urllib.parse.parse_qs(raw)

        android_app_id = form.get("android_app_id", [""])[0].strip()
        ios_app_id = form.get("ios_app_id", [""])[0].strip()
        country = form.get("country", ["tw"])[0].strip().lower()
        keywords = parse_keywords(form.get("keywords", [""])[0])

        if not android_app_id or not ios_app_id or not keywords:
            self.respond_html(render_page())
            return

        rows = []
        for kw in keywords:
            rows.append({"platform": "Android", "keyword": kw, "rank": get_google_play_rank(kw, android_app_id, country=country)})
            rows.append({"platform": "iOS", "keyword": kw, "rank": get_app_store_rank_by_id(kw, ios_app_id, country=country)})

        save_check(country, android_app_id, ios_app_id, keywords, rows)
        self.respond_html(
            render_page(
                result_rows=rows,
                selected_country=country,
                android_app_id=android_app_id,
                ios_app_id=ios_app_id,
                keywords_text="\n".join(keywords),
            )
        )

    def respond_html(self, body: str):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"ASO panel running on http://{HOST}:{PORT}")
    server.serve_forever()
