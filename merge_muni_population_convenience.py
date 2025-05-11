#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_population_convenience.py

 - 市区町村別の人口とコンビニ件数をマージして CSV 出力
 - 人口は e-Stat API から取得した国勢調査 2020（速報値）を使用
 - コンビニ件数は ApamanShop の市区町村別コンビニ件数ランキングを使用
 - 欠損行は一覧表示

 - 入力:
       - municipality_population_2020.csv ... 市区町村別の人口
       - convenience_by_municipality.csv ... コンビニ件数
 - 出力:
       - muni_pop_conv.csv ... area_code, area_name, population, conv_store
"""

from __future__ import annotations
from pathlib import Path
import unicodedata as ud
import re
import pandas as pd

DIR = Path("./data")
CSV_POP = DIR / "municipality_population_2020.csv"
CSV_CVS = DIR / "convenience_by_municipality.csv"
CSV_OUT = DIR / "muni_pop_conv.csv"

# ──────────────────────────────────────────────
PREFS = (
    "北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 "
    "埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 "
    "岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 "
    "鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 "
    "佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県"
).split()

pref_rx = re.compile(rf"^({'|'.join(PREFS)})")   # 先頭の都道府県
gun_rx  = re.compile(r"^[^\s　]+郡")             # 先頭の郡名（○○郡）

def normalize(name: str | float) -> str:
    if pd.isna(name):
        return ""
    s = ud.normalize("NFKC", str(name)).strip().replace("　", "")
    s = pref_rx.sub("", s, count=1)   # 都道府県を1回だけ削除
    s = gun_rx.sub("", s, count=1)    # 郡名があれば削除
    return s

# ──────────────────────────────────────────────
def main() -> None:
    # --- 人口 CSV ------------------------------------------------
    df_pop = (
        pd.read_csv(CSV_POP, dtype=str)
          .loc[:, ["area_code", "area_name", "population"]]
    )
    df_pop["key"] = df_pop["area_name"].map(normalize)

    # --- コンビニ CSV --------------------------------------------
    df_cvs = (
        pd.read_csv(CSV_CVS, dtype=str)
          .rename(columns={"municipality": "area_name"})
          .loc[:, ["area_name", "conv_store"]]
    )
    df_cvs["key"] = df_cvs["area_name"].map(normalize)

    # --- マージ --------------------------------------------------
    df = (
        df_pop.merge(df_cvs[["key", "conv_store"]], on="key", how="left")
              .drop(columns="key")
              .loc[:, ["area_code", "area_name", "population", "conv_store"]]
              .sort_values("area_code")
    )

    # --- 欠損行を出力 -------------------------------------------
    missing = df[df["conv_store"].isna()]
    if not missing.empty:
        print("\n[missing] conv_store が取得できなかった市区町村一覧")
        print("-" * 60)
        for _, r in missing.iterrows():
            print(f"{r['area_code']:>5s}  {r['area_name']}  (人口: {r['population']})")
        print(f"- 計 {len(missing):,} 件が欠損 -\n")

    # --- CSV 書き出し -------------------------------------------
    CSV_OUT.parent.mkdir(exist_ok=True, parents=True)
    df.to_csv(CSV_OUT, index=False, encoding="utf-8-sig")

    hit  = len(df) - len(missing)
    miss = len(missing)
    print(f"[done] {len(df):,} 行を書き出しました → {CSV_OUT.resolve()}")
    print(f"       コンビニ件数付き : {hit:,} 行 / 欠損 : {miss:,} 行")

# ──────────────────────────────────────────────
if __name__ == "__main__":
    main()
