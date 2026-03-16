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
    conn.executemany(
        "INSERT INTO rankings (check_id, platform, keyword, rank_text) VALUES (?, ?, ?, ?)",
        [(check_id, r["platform"], r["keyword"], r["rank"]) for r in rows],
    )
    conn.commit()
    conn.close()


def get_recent_checks(limit: int = 10) -> list[dict[str, Any]]:
    conn = get_conn()
    checks = conn.execute(
        "SELECT id, created_at, country, android_app_id, ios_app_id FROM checks ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    payload: list[dict[str, Any]] = []
    for c in checks:
        rankings = conn.execute(
            "SELECT platform, keyword, rank_text FROM rankings WHERE check_id = ? ORDER BY platform, keyword",
            (c["id"],),
        ).fetchall()
        payload.append({"check": dict(c), "rankings": [dict(r) for r in rankings]})
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
