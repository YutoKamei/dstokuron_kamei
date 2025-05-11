#!/usr/bin/env python3
"""
estat_population_muni2020.py

 - e-Stat 国勢調査 2020（速報値）―市町村別・総人口を CSV 出力

 - 入力 : statsData_0003433219.json   … e-Stat API から取得した JSON ファイル
 - 出力 : municipality_population_2020.csv  … area_code, area_name, population
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

# ファイルパス（必要に応じて変更）
JSON_FILE = Path("./data/statsData_0003433219.json")
CSV_FILE = Path("./data/municipality_population_2020.csv")


def load_json(path: Path) -> Dict[str, Any]:
    """JSON ファイルを読み込んで辞書を返す。"""
    with path.open(encoding="utf-8") as fp:
        return json.load(fp)


def build_area_map(data: Dict[str, Any]) -> Dict[str, str]:
    """area コード → 市町村名 の対応表を作成。"""
    class_objs = data["GET_STATS_DATA"]["STATISTICAL_DATA"]["CLASS_INF"]["CLASS_OBJ"]
    area_classes = next(obj["CLASS"] for obj in class_objs if obj["@id"] == "area")
    return {cls["@code"]: cls["@name"] for cls in area_classes}


def extract_population_rows(
    data: Dict[str, Any], area_map: Dict[str, str]
) -> List[Dict[str, Optional[int]]]:
    """
    総人口 (@cat01 = 0) の VALUE レコードを抽出し、
    area_code / area_name / population 形式のリストを返す。
    """
    rows = []
    for rec in data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]:
        # @tab 2020_01 = 人口,  @cat01 0 = 総数
        if rec["@tab"] == "2020_01" and rec["@cat01"] == "0":
            val = rec["$"]
            population = int(val.replace(",", "")) if val not in ("", "-") else None
            rows.append(
                {
                    "area_code": rec["@area"],
                    "area_name": area_map.get(rec["@area"], ""),
                    "population": population,
                }
            )
    # area_code 昇順に並べ替え
    rows.sort(key=lambda r: r["area_code"])
    return rows


def save_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    """DictWriter で CSV 出力 (UTF-8 BOM 付き)。"""
    with path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["area_code", "area_name", "population"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    data = load_json(JSON_FILE)
    area_map = build_area_map(data)
    rows = extract_population_rows(data, area_map)
    save_csv(rows, CSV_FILE)
    print(f"[OK] Saved → {CSV_FILE.resolve()}")


if __name__ == "__main__":
    main()
