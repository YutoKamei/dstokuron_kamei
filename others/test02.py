#!/usr/bin/env python3
"""
fetch_one_muni_traffic.py
-------------------------
■ 目的
    ・市区町村コードを 1 つ指定し，
      その自治体内に設置された常設トラカンの “5 分値” 交通量を取得・集計します。

■ 前提ファイル
    ../data/municipality_2020.gpkg         … merge_muni_boundary.py で作成した境界
      └─ レイヤ名 : muni2020

■ 取得 API
    https://api.jartic-open-traffic.org/geoserver
    (レイヤ `t_travospublic_measure_5m`)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point
import sys

# ───────────────────────────────────────────────────────────────
# 1. 設定
# ───────────────────────────────────────────────────────────────
TARGET_CODE = "01101"               # ← テストしたい自治体コードを変更
TIMECODE    = 202505130900          # 例：2025/5/13 09:00
ROAD_TYPE   = "3"                   # 3 = 一般国道, 2 = 高速道路 …など

GPKG_PATH   = Path("../data/municipality_2020.gpkg")
LAYER_NAME  = "muni2020"

BASE_URL    = "https://api.jartic-open-traffic.org/geoserver"
TYPE_NAME   = "t_travospublic_measure_5m"

# ───────────────────────────────────────────────────────────────
# 2. 補助関数
# ───────────────────────────────────────────────────────────────
def detect_code_column(gdf: gpd.GeoDataFrame) -> str:
    """市区町村コード列を推測して返す（前回説明の強化版）"""
    priority = [
        "JCODE", "KEY_CODE", "CITYCODE", "CITY_CODE",
        "N03_007", "area_code", "市区町村コード", "code",
    ]
    for col in priority:
        if col in gdf.columns:
            return col

    # fallback: 列名に code が入り 5〜6 桁の数値
    for col in gdf.columns:
        if "code" in col.lower():
            try:
                sample = str(gdf[col].dropna().iloc[0])
                if sample.isdigit() and 5 <= len(sample) <= 6:
                    return col
            except IndexError:
                pass

    raise KeyError(f"市区町村コード列を判定できません: {list(gdf.columns)}")


def build_params(bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    """JARTIC WFS パラメータを生成"""
    xmin, ymin, xmax, ymax = bbox
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


def fetch_points(bbox: tuple[float, float, float, float]) -> pd.DataFrame:
    """API から GeoJSON を取得し DataFrame へ"""
    r = requests.get(BASE_URL, params=build_params(bbox), timeout=60)
    r.raise_for_status()
    gj = r.json()

    rows: list[dict[str, Any]] = []
    for feat in gj.get("features", []):
        prop = feat["properties"].copy()

        # point (lon, lat)
        if feat.get("geometry"):
            lon, lat = feat["geometry"]["coordinates"][0]
            prop["geometry"] = Point(lon, lat)
        rows.append(prop)

    df = pd.DataFrame(rows)
    if df.empty:
        return gpd.GeoDataFrame(df)  # 空でも GeoDataFrame を返す

    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    gdf = gdf.rename(columns={"交通量": "traffic_volume", "平均速度": "avg_speed",
                              "地点コード": "point_code"})
    return gdf


# ───────────────────────────────────────────────────────────────
# 3. main
# ───────────────────────────────────────────────────────────────
def main() -> None:
    # ① 自治体境界をロードし，対象自治体のポリゴンを抽出
    muni_all = gpd.read_file(GPKG_PATH, layer=LAYER_NAME)
    code_col = detect_code_column(muni_all)

    target_poly = muni_all.loc[muni_all[code_col] == TARGET_CODE]
    if target_poly.empty:
        raise SystemExit(f"[ERROR] コード {TARGET_CODE} が GPKG に見つかりません")

    poly = target_poly.geometry.values[0]
    bbox = poly.bounds  # (xmin, ymin, xmax, ymax)

    print(f"[step] コード {TARGET_CODE} の境界 BBOX = {bbox}")

    # ② JARTIC API で 5 分値ポイントを取得
    pts = fetch_points(bbox)
    print(f"[step] 取得ポイント数: {len(pts):,}")

    if pts.empty:
        print("[warn] 該当ポイントがありませんでした")
        return

    # ③ ポイントを自治体ポリゴンに spatial join（厳密に内部判定）
    pts_in = pts[pts.within(poly)]
    if pts_in.empty:
        print("[warn] ポイントが自治体境界内にありませんでした")
        return

    total_volume = pts_in["traffic_volume"].sum()
    print("────────────────────────────────────────")
    print(f"自治体コード : {TARGET_CODE}")
    print(f"時間コード   : {TIMECODE}")
    print(f"道路種別     : {ROAD_TYPE}")
    print(f"対象ポイント : {len(pts_in):,} 箇所")
    print(f"総交通量     : {int(total_volume):,} 台 / 5 分")
    print("────────────────────────────────────────")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[cancel] 中断しました", file=sys.stderr)
    except requests.HTTPError as e:
        print(f"[HTTPError] {e.response.status_code} : {e.response.text[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
