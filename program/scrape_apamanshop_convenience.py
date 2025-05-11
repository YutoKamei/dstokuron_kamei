#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape_apamanshop_convenience.py

 - ApamanShop「市区町村別コンビニ件数ランキング」
 - 市区町村別のコンビニ件数をスクレイピングして CSV 出力
 - 95 ページ分巡回して、市区町村名と店舗数を取得

 - 出力 : convenience_by_municipality.csv ... municipality, conv_store
 - 参考 : https://www.apamanshop.com/townpage/ranking/town-convenience/
"""

from __future__ import annotations
import csv
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ───────────── 設定値 ──────────────────────────────────────────
BASE_URL   = "https://www.apamanshop.com/townpage/ranking/town-convenience/{}/"
START_PAGE = 1          # 1 〜 95 で固定
END_PAGE   = 95
SLEEP_SEC  = 1.0        # サーバ負荷軽減用ウエイト
OUT_CSV    = Path("../data/convenience_by_municipality.csv")
HEADERS    = {
    # 普通のブラウザっぽい UA を入れておく
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}
# ────────────────────────────────────────────────────────────────


def fetch_page(page: int) -> BeautifulSoup:
    """対象ページを GET → BeautifulSoup オブジェクトを返す"""
    url = BASE_URL.format(page)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def parse_table_rows(soup: BeautifulSoup) -> list[tuple[str, int]]:
    """
    <tbody><tr>… を走査して
    (市区町村名, コンビニ件数) のタプルをリストで返す
    """
    results: list[tuple[str, int]] = []

    # ApamanShop 側の HTML は「唯一のランキングテーブル」がある前提で
    # CSS セレクタで tbody/tr を抽出
    for tr in soup.select("section table tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue

        # 1列目リンク内テキスト＝市区町村名
        name = tds[0].get_text(strip=True)

        # 2列目＝コンビニ件数（カンマ入りを除去して int 化）
        count_txt = tds[1].get_text(strip=True).replace(",", "")
        if not count_txt.isdigit():
            continue
        count = int(count_txt)

        results.append((name, count))

    return results


def main() -> None:
    rows: list[tuple[str, int]] = []

    print("[step] ApamanShop 95 ページをスクレイピング中…")
    for page in tqdm(range(START_PAGE, END_PAGE + 1)):
        soup = fetch_page(page)
        rows.extend(parse_table_rows(soup))
        time.sleep(SLEEP_SEC)

    # CSV 出力
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["municipality", "conv_store"])
        writer.writerows(rows)

    print(f"[done] {len(rows):,} 行を書き出しました → {OUT_CSV.resolve()}")


if __name__ == "__main__":
    main()
