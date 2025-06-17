import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib  # 日本語表示に対応
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
import numpy as np
import logging

# --- 0. ログ設定 ---
LOG_FILE = 'data/log/linear-regression_analysis_log.txt'

# ロガーを設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 以前のハンドラが残っている場合はクリアする
if logger.hasHandlers():
    logger.handlers.clear()

# ログのフォーマットを設定
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# ファイルへのハンドラを設定（実行のたびに上書き）
file_handler = logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# コンソールへのハンドラを設定
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# --- 1. データの準備 ---
# ご指定のCSVファイルを読み込む
try:
    df = pd.read_csv('data/muni_pop_conv.csv')
except FileNotFoundError:
    logger.info("エラー: 'data/muni_pop_conv.csv' が見つかりません。")
    logger.info("スクリプトと同じ階層にファイルを配置してください。")
    exit()

# ご指定の列名 'area_name', 'population', 'conv_store' を使用してデータを準備
# 不要な列はここで除外します
try:
    df_analysis = df[['area_name', 'population', 'conv_store']].copy()
except KeyError:
    logger.error("エラー: CSVファイルに 'area_name', 'population', 'conv_store' のいずれかの列が存在しません。")
    logger.error(f"検出された列名: {df.columns.tolist()}")
    exit()


# 欠損値（人口やコンビニ数が不明な市区町村）がある場合は除外する
df_analysis.dropna(inplace=True)

# 人口0の市区町村は分析から除外（対数変換のため）
df_analysis = df_analysis[df_analysis['population'] > 0]

logger.info("--- データ読み込みと前処理完了 ---")
logger.info(f"分析対象の市区町村数: {len(df_analysis)}件")
logger.info("読み込んだデータの先頭5行:")
logger.info(df_analysis.head())


# --- 2. 回帰分析 (人口からコンビニ店舗数を予測) ---
logger.info("--- 1. 回帰分析を開始します ---")
# 説明変数 X (人口) と 目的変数 y (コンビニ店舗数)
# 正しい列名 'population' と 'conv_store' を使用
X = df_analysis[['population']]
y = df_analysis['conv_store']

# 回帰モデルの学習
model = LinearRegression()
model.fit(X, y)

# 分析結果の取得
a = model.coef_[0]  # 回帰係数
b = model.intercept_ # 切片
r2 = model.score(X, y) # 決定係数

logger.info(f"回帰式: conv_store = {a:.5f} * population + {b:.2f}")
logger.info(f"決定係数 (R^2): {r2:.3f}")
logger.info(f"解釈: 人口が1万人増えると、コンビニが約{a*10000:.1f}店舗増える傾向にあります。")

# 回帰分析の結果を可視化
plt.figure(figsize=(10, 6))
plt.scatter(X, y, alpha=0.5, label='実際のデータ')
plt.plot(X, model.predict(X), color='red', linewidth=2, label='回帰直線')
# グラフ内に表示するテキストを作成 (決定係数 R^2 も追記)
equation_text = f'y = {a:.5f}x + {b:.2f}\n$R^2$ = {r2:.3f}'
# グラフの(x, y) = (50000, 400)の位置にテキストを配置
plt.text(750000, 50, equation_text, fontsize=12, bbox=dict(facecolor='white', alpha=0.5))
plt.title('人口とコンビニ店舗数の関係（回帰分析）')
plt.xlabel('市区町村の人口 (population)')
plt.ylabel('コンビニ店舗数 (conv_store)')
plt.grid(True)
plt.legend()
plt.savefig('data/pictures/regression_analysis_final.png', dpi=400) # 画像として保存
logger.info("回帰分析のグラフを 'regression_analysis_final.png' として保存しました。")

logger.info("分析が完了しました。")