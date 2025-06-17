#!/usr/bin/env python3
"""
fetch_all_muni_traffic.py
-------------------------
• municipality_2020.gpkg を読み込み、各市区町村ポリゴン bbox で
  JARTIC 5 分値（t_travospublic_measure_5m）を取得
• 取得日時は TIMECODE（YYYYMMDDhhmm）で一括指定
• 出力: ../data/traffic_by_municipality_<TIMECODE>.csv
"""

from __future__ import annotations
import sys, time, json, logging
from pathlib import Path
from typing import Any, Optional

import requests
import pandas as pd
import geopandas as gpd
from tqdm import tqdm

# ────────────────────────────────
# 0. 設定
# ────────────────────────────────
GPKG_PATH   = Path("../data/municipality_2020.gpkg")
LAYER       = "muni2020"
OUT_DIR     = Path("../data")
TIMECODE    = 202505130900        # ← 取得したい日時を変更
ROAD_TYPE   = "3"                 # 3 = 一般国道, 2 = 高速道路
BASE_URL    = "https://api.jartic-open-traffic.org/geoserver"
TYPE_NAME   = "t_travospublic_measure_5m"
SLEEP_SEC   = 0.5                 # API 過負荷回避
MAX_RETRY   = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ────────────────────────────────
# 1. ユーティリティ
# ────────────────────────────────
# --- 修正版 detect_code_column ---------------------------------
def detect_code_column(gdf: gpd.GeoDataFrame) -> str:
    """
    市区町村コード列を自動判定して返す
    1. 優先候補リストで先頭ヒット
    2. fallback: 「code を含む列名」のうちレコード長 5〜6 桁のもの
    """
    # 1) 優先候補（必要に応じて追加してください）
    priority = [
        "JCODE", "KEY_CODE",              # 統計 GIS 典型
        "area_code", "CITYCODE", "CITY_CODE",
        "N03_007",                        # 国交省 N03 データ
        "市区町村コード", "code",
    ]
    for col in priority:
        if col in gdf.columns:
            return col

    # 2) fallback
    for col in gdf.columns:
        if "code" in col.lower():
            # 値が 5〜6 桁数値なら市区町村コードとみなす
            try:
                sample = str(gdf[col].dropna().iloc[0])
                if sample.isdigit() and 5 <= len(sample) <= 6:
                    return col
            except IndexError:
                pass

    raise KeyError(
        "市区町村コード列が見つかりません。\n"
        f"取得できた列: {list(gdf.columns)}\n"
        "detect_code_column() に列名を追加してください。"
    )
# ----------------------------------------------------------------

def build_params(bbox: tuple[float, float, float, float]) -> dict[str, Any]:
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

def request_api(params: dict[str, Any]) -> Optional[dict]:
    """API 1 回呼び出し（リトライ付き）"""
    for i in range(1, MAX_RETRY + 1):
        try:
            r = requests.get(BASE_URL, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logging.warning(f"  └ retry {i}/{MAX_RETRY} ({e})")
            time.sleep(SLEEP_SEC * 2)
    return None

def calc_volume(props: dict[str, Any]) -> int:
    """仕様書の 18 列を合算して総交通量を返す"""
    keys = [
        "上り・小型交通量", "上り・大型交通量", "上り・車種判別不能交通量",
        "下り・小型交通量", "下り・大型交通量", "下り・車種判別不能交通量",
    ]
    return sum(int(props.get(k, 0)) for k in keys)

# ────────────────────────────────
# 2. main
# ────────────────────────────────
def main() -> None:
    if not GPKG_PATH.exists():
        sys.exit(f"[ERROR] {GPKG_PATH} がありません。merge_muni_boundary.py を先に実行してください")

    gdf = gpd.read_file(GPKG_PATH, layer=LAYER)
    code_col = detect_code_column(gdf)
    logging.info(f"市区町村数 {len(gdf):,} 件の交通量を取得します")

    results = []

    for _, row in tqdm(gdf.iterrows(), total=len(gdf), unit="muni"):
        muni_code: str = str(row[code_col])
        bbox = row.geometry.bounds  # (xmin, ymin, xmax, ymax)

        params = build_params(bbox)
        data = request_api(params)
        time.sleep(SLEEP_SEC)

        if not data or not data.get("features"):
            continue  # データなし

        # 同一市区町村内に複数計測点があれば合算
        total = 0
        for feat in data["features"]:
            props = feat["properties"]
            total += calc_volume(props)

        results.append(
            {
                "muni_code": muni_code,
                "datetime": TIMECODE,
                "traffic_volume": total,
                "points": len(data["features"]),
            }
        )

    if not results:
        sys.exit("[warn] 取得件数 0。対象時間にデータが存在しない可能性があります")

    df_out = pd.DataFrame(results)
    OUT_DIR.mkdir(exist_ok=True)
    out_csv = OUT_DIR / f"traffic_by_municipality_{TIMECODE}.csv"
    df_out.to_csv(out_csv, index=False, encoding="utf-8")
    logging.info(f"[done] {len(df_out):,} 行を書き出しました → {out_csv}")

# ────────────────────────────────
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("[cancel] 中断しました")
    except requests.HTTPError as e:
        sys.exit(f"[HTTPError] {e.response.status_code} : {e.response.text[:200]}")
    except Exception as e:
        sys.exit(f"[ERROR] {e}")
