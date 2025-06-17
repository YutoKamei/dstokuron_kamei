#!/usr/bin/env python3
"""
download_muni_shapefiles.py

 - e-Statの統計地理情報システムから境界データを自治体単位でダウンロードし、都道府県別フォルダへ展開保存する。

 - 入力:
       - ../data/muni_pop_conv.csv   （area_code 列を使用）

 - 出力:
       - ../data/shapefile/{pref_code}/{muni_code}/…
       - 例: 北海道札幌市中央区 (01101) → ../data/shapefile/01/01101/…
"""

from __future__ import annotations
import sys, time, zipfile
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests
from tqdm import tqdm

# ───────────────────────────────
# 1. 設定
# ───────────────────────────────
CSV_PATH  = Path("../data/muni_pop_conv.csv").resolve()
OUT_DIR   = Path("../data/shapefile").resolve()

BASE_URL  = "https://www.e-stat.go.jp/gis/statmap-search/data"
DL_ID     = "A002005212020"          # 2020 市区町村界
COORD_SYS = "1"                      # 1 = WGS84
FORMAT    = "shape"                  # Shapefile
DL_TYPE   = "5"                      # 5 = 市区町村界
SLEEP_SEC = 0.4                      # polite pause

# ───────────────────────────────
# 2. 関数
# ───────────────────────────────
def build_url(muni_code: str) -> str:
    p: Dict[str, str] = {
        "dlserveyId": DL_ID,
        "code": muni_code,
        "coordSys": COORD_SYS,
        "format": FORMAT,
        "downloadType": DL_TYPE,
    }
    return BASE_URL + "?" + "&".join(f"{k}={v}" for k, v in p.items())


def fetch_zip(url: str, dest_zip: Path) -> bool:
    """
    URL から ZIP をダウンロードし dest_zip に保存
    True=成功 / False=失敗（HTTP エラーなど）
    """
    if dest_zip.exists():
        return True

    # ── 親フォルダを必ず作成 ──
    dest_zip.parent.mkdir(parents=True, exist_ok=True)

    try:
        r = requests.get(url, timeout=120)
        r.raise_for_status()
    except requests.HTTPError as e:
        print(f"    [HTTP {e.response.status_code}] {dest_zip.name} skip")
        return False

    dest_zip.write_bytes(r.content)
    return True


def extract_zip(zip_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)


def load_muni_codes(csv_path: Path) -> List[str]:
    """CSV から実際の自治体コード（5桁・末尾≠000）を抽出"""
    df = pd.read_csv(csv_path, dtype=str)
    if "area_code" not in df.columns:
        sys.exit("[ERROR] 'area_code' 列が見つかりません")

    codes = []
    for c in df["area_code"].unique():
        c = str(c).zfill(5)
        if len(c) == 5 and c[2:] != "000":   # 市区町村のみ
            codes.append(c)
    return sorted(codes)

# ───────────────────────────────
# 3. main
# ───────────────────────────────
def main() -> None:
    if not CSV_PATH.exists():
        sys.exit(f"[ERROR] 入力 CSV が見つかりません → {CSV_PATH}")

    muni_codes = load_muni_codes(CSV_PATH)
    print(f"[step] 自治体数 {len(muni_codes):,} 件の Shapefile を取得します")

    success = fail = 0
    for code in tqdm(muni_codes, ncols=80):
        pref_code = code[:2]
        pref_dir  = OUT_DIR / pref_code
        zip_path  = pref_dir / f"{code}.zip"
        muni_dir  = pref_dir / code

        if not fetch_zip(build_url(code), zip_path):
            fail += 1
            continue

        try:
            extract_zip(zip_path, muni_dir)
            success += 1
        except zipfile.BadZipFile:
            print(f"    [Bad ZIP] {code} skip")
            fail += 1
            zip_path.unlink(missing_ok=True)

        time.sleep(SLEEP_SEC)

    print(f"[done] 成功: {success:,} / 失敗: {fail:,}")

# ───────────────────────────────
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("[cancel] 中断しました")
