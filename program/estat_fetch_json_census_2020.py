#!/usr/bin/env python3
"""
estat_fetch_json_census_2020.py

 - 国勢調査 2020（速報値）―市町村別・総人口を取得
 - 統計データ ID : 0003433219
 - e-Stat API から取得

 - 出力 : statsData_0003433219.json
 - 参考 : https://www.e-stat.go.jp/api/api-info/e-stat-manual
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from dotenv import load_dotenv

# .envファイルの内容を読み込む
load_dotenv()

# appId を環境変数から取得
# 環境変数 APP_ID に e-Stat API のアプリ ID を設定しておくこと
APP_ID = os.environ['APP_ID']

ENDPOINT = (
    "http://api.e-stat.go.jp/rest/3.0/app/json/getStatsData?"
    "lang=J&statsDataId=0003433219&metaGetFlg=Y&cntGetFlg=N&"
    "explanationGetFlg=Y&annotationGetFlg=Y&sectionHeaderFlg=1&"
    "replaceSpChars=0"
)
OUTPUT_FILE = "../data/statsData_0003433219.json"


def build_url() -> str:
    """appId 付き URL を返す。"""
    if not APP_ID:
        sys.exit("[ERROR] APP_ID が設定されていません。")
    return ENDPOINT + "&" + urllib.parse.urlencode({"appId": APP_ID})


def fetch_json(url: str) -> dict:
    """URL から JSON を取得して Python オブジェクトへ変換。"""
    with urllib.request.urlopen(url) as resp:
        if resp.status != 200:
            sys.exit(f"[ERROR] HTTP {resp.status}: {resp.reason}")
        data = json.load(resp)

    # e-Stat 独自の RESULT ステータスも確認
    result = data.get("GET_STATS_DATA", {}).get("RESULT", {})
    if result.get("STATUS") != 0:
        sys.exit(f"[ERROR] e-Stat API error: {result}")
    return data


def main() -> None:
    url = build_url()
    print(f"[INFO] Requesting: {url}")

    data = fetch_json(url)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    print(f"[OK] Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()