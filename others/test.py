#!/usr/bin/env python3
"""
fetch_jartic_5min.py
--------------------
• 常設トラカン 5 分値（t_travospublic_measure_5m）を取得  
• GeoJSON → pandas.DataFrame へ変換  
• area_code / datetime / traffic_volume などの属性を CSV に保存

"""

from __future__ import annotations
import os
import sys
import time
import json
from pathlib import Path
from typing import Any

import requests
import pandas as pd

# ───────────────────────────────────────────────────────────────
# 0. 設定 ────────────────────────────────────────────────────────
OUT_CSV = Path("../data/jartic_5min_sample.csv")  # 出力先

BBOX = (139.65, 35.65, 139.75, 35.75)   # xmin, ymin, xmax, ymax (東京・新宿周辺)
TIMECODE = 202505130900                 # YYYYMMDDhhmm （例：2025/5/13 09:00）
ROAD_TYPE = "3"                         # 3=一般国道, 2=高速道路 など

BASE_URL = "https://api.jartic-open-traffic.org/geoserver"
TYPE_NAME = "t_travospublic_measure_5m"

# ───────────────────────────────────────────────────────────────
def build_params() -> dict[str, Any]:
    """WFS パラメータを生成"""
    xmin, ymin, xmax, ymax = BBOX
    cql = (
        f"道路種別='{ROAD_TYPE}' AND "
        f"時間コード={TIMECODE} AND "
        f"BBOX(ジオメトリ,{xmin},{ymin},{xmax},{ymax},'EPSG:4326')"
    )
    return {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": TYPE_NAME,
        "srsName": "EPSG:4326",
        "outputFormat": "application/json",
        "exceptions": "application/json",
        "cql_filter": cql,
    }


def fetch_geojson() -> dict:
    """API から GeoJSON を取得"""

    r = requests.get(BASE_URL, params=build_params(), timeout=60)
    r.raise_for_status()
    return r.json()


def geojson_to_df(gj: dict) -> pd.DataFrame:
    """GeoJSON → DataFrame"""
    rows: list[dict[str, Any]] = []
    for feat in gj.get("features", []):
        prop = feat["properties"].copy()

        # ジオメトリ（ポイント）は coordinates[0] に (lon, lat)
        if feat.get("geometry"):
            lon, lat = feat["geometry"]["coordinates"][0]
            prop["longitude"] = lon
            prop["latitude"]  = lat
        rows.append(prop)

    return pd.DataFrame(rows)


def main() -> None:
    print("[step] JARTIC 5 分値を取得中…")
    gj = fetch_geojson()
    print(f"   └─ 取得件数: {gj.get('numberReturned', 0)}")

    df = geojson_to_df(gj)
    if df.empty:
        print("[warn] データが 0 件でした")
        return

    # 列名など最低限の整形例
    df = df.rename(columns={
        "地点コード": "point_code",
        "交通量": "traffic_volume",
        "平均速度": "avg_speed",
    })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")
    print(f"[done] {len(df):,} 行を書き出しました → {OUT_CSV}")


# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("[cancel] 中断しました")
    except requests.HTTPError as e:
        sys.exit(f"[HTTPError] {e.response.status_code} : {e.response.text[:200]}")
    except Exception as e:
        sys.exit(f"[ERROR] {e}")
