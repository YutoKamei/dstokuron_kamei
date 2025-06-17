#!/usr/bin/env python3
"""
merge_muni_boundary.py

 - ../data/shapefile/ 以下に保存した 自治体単位 の Shapefileを読み込み、単一の GeoPackage (municipality_2020.gpkg / レイヤ muni2020)に統合する。

 - 入力:
       - ../data/shapefile/{pref_code}/{muni_code}/…

 - 出力:
       - ../data/municipality_2020.gpkg

"""

from __future__ import annotations
from pathlib import Path
import geopandas as gpd

# ───────────────────────────────
# 1. 設定
# ───────────────────────────────
SHP_ROOT    = Path("../data/shapefile").resolve()   # ← 県別フォルダの親
OUT_GPKG    = Path("../data/municipality_2020.gpkg").resolve()
LAYER_NAME  = "muni2020"

# ───────────────────────────────
# 2. 関数
# ───────────────────────────────
def collect_shp() -> list[Path]:
    """
    県フォルダ (../data/shapefile/01, 02, …) を再帰検索し、
    最初に見つかった *.shp を 1 自治体 1 件としてリスト化
    """
    if not SHP_ROOT.exists():
        raise SystemExit(f"[ERROR] {SHP_ROOT} が見つかりません。"
                         "先に download_muni_shapefiles.py を実行してください")

    return sorted(SHP_ROOT.rglob("*.shp"))

def merge(shp_paths: list[Path]) -> None:
    if not shp_paths:
        raise SystemExit("[ERROR] Shapefile が 1 件も見つかりません")

    gdfs = []
    for p in shp_paths:
        try:
            gdf = gpd.read_file(p, encoding="cp932")
        except UnicodeDecodeError:
            # 万一 CP932 で読めなければ UTF-8 を試行
            gdf = gpd.read_file(p, encoding="utf-8")
        gdfs.append(gdf)

    merged = gpd.pd.concat(gdfs, ignore_index=True)

    OUT_GPKG.parent.mkdir(exist_ok=True)
    merged.to_file(OUT_GPKG, layer=LAYER_NAME, driver="GPKG")
    print(f"[done] {OUT_GPKG} に {len(merged):,} features を保存しました。")

# ───────────────────────────────
# 3. main
# ───────────────────────────────
def main() -> None:
    shp_files = collect_shp()
    print(f"[step] Shapefile 読込: {len(shp_files):,} 件を統合します")
    merge(shp_files)

if __name__ == "__main__":
    main()
