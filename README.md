# 市区町村別 **人口 × コンビニ件数** データ分析

このリポジトリでは、以下 3 種類のデータソースを突合し、`muni_pop_conv.csv`（人口とコンビニ件数一覧）を生成したうえで、**単回帰分析**により、人口とコンビニ店舗数の関係を検証します。

* **e-Stat 国勢調査 2020（速報値）** … 市区町村別総人口
* **アパマンショップ** … 市区町村別コンビニ店舗数ランキング
* （作業用）中間 CSV／JSON ファイル

> 対象市区町村：全国 1,965 自治体（都道府県・政令市区を含む）

---

## ディレクトリ構成

```
.
├─ data/                # 生成物・中間ファイル置き場
│  ├─ log/
│  │  └─ linear-regression_analysis_log.txt  # 回帰分析プログラム実行時のログ
│  ├─ pictures/
│  │  └─ regression_analysis_final.png    # 回帰分析の結果グラフ
│  ├─ statsData_0003433219.json           # e‑Stat API 生データ
│  ├─ municipality_population_2020.csv    # 市区町村別人口（CSV）
│  ├─ convenience_by_municipality.csv     # コンビニ件数（CSV）
│  └─ muni_pop_conv.csv                   # ★最終成果物
├─ program/                # Pythonコード置き場
|  ├─ estat_fetch_json_census_2020.py        # (1) 国勢調査 JSON 取得
|  ├─ estat_population_muni2020.py           # (2) 人口 CSV 生成
|  ├─ scrape_apamanshop_convenience.py       # (3) コンビニ件数 CSV 生成
|  ├─ merge_muni_population_convenience.py   # (4) マージ＆欠損出力
|  └─ linear-regression_analysis.py          # (5) 回帰分析
├─ .gitignore
├─ requirements.txt
├─ .env                                   # e‑Stat APP_ID を格納（後述）
└─ README.md
```

---

## セットアップ

1. **Python 3.8 以上** を用意します。

2. 依存ライブラリをインストールします。

   ```bash
   pip install -r requirements.txt
   ```

3. **e‑Stat API の APP\_ID を取得**し、プロジェクト直下に `.env` を作成して次の 1 行を記述します。

   ```dotenv
   APP_ID=自身のアプリID
   ```

---

## 実行フロー

1. ### 国勢調査 JSON を取得

   ```bash
   python estat_fetch_json_census_2020.py
   ```

   * 出力: `data/statsData_0003433219.json`

2. ### JSON → 市区町村別人口 CSV へ変換

   ```bash
   python estat_population_muni2020.py
   ```

   * 出力: `data/municipality_population_2020.csv`

3. ### アパマンショップのサイト からコンビニ件数をスクレイピング

   ```bash
   python scrape_apamanshop_convenience.py
   ```

   * 全 95 ページを巡回し 1,965 行を取得します。
     サーバ負荷対策として 1 秒間隔でアクセスしています。
   * 出力: `data/convenience_by_municipality.csv`

4. ### 人口 × コンビニ件数 の突合

   ```bash
   python merge_muni_population_convenience.py
   ```

   * ノーマライズ規則

     * 先頭の **都道府県名** と **○○郡** を削除し、市区町村名のみでマッチします。
     * Unicode NFKC 正規化 + 全角スペース削除。
   * 欠損（片方にのみ存在）自治体をコンソールへ一覧表示します。
   * 出力: `data/muni_pop_conv.csv`

     * 列: `area_code, area_name, population, conv_store`

5. ### 人口からコンビニ店舗数を予測（回帰分析）

   ```bash
   python program/linear-regression_analysis.py
   ```

   * 読み込みファイル  
     * `data/muni_pop_conv.csv`  
   * 出力ファイル  
     * `data/log/linear-regression_analysis_log.txt` … 実行ログ（回帰式・決定係数など）  
     * `data/pictures/regression_analysis_final.png` … 散布図＋回帰直線  

   > デフォルトでは人口ゼロの自治体と欠損値は除外します。

---

## 注意・トラブルシュート

| 症状                                       | 原因 / 対処                                                            |
| ---------------------------------------- | ------------------------------------------------------------------ |
| `APP_ID が設定されていません` と表示                  | `.env` が見つからない / APP\_ID が未設定です。                                   |
| スクレイピングが途中で失敗する                          | ネットワーク断や HTML 構造変更。リトライ、または `END_PAGE` を減らして確認。                    |
| `muni_pop_conv.csv` に `conv_store` が NaN | 市区町村名表記ゆれ。正規化ルールを追加して再実行するか、手動で補完してください。                           |

---

