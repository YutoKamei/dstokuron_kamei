import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib  # 日本語表示に対応
from sklearn.cluster import KMeans
import numpy as np
import logging

# --- 0. ログ設定 ---
LOG_FILE = 'data/log/clustering_analysis_log.txt'

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

# --- 2. クラスタリング (市区町村のパターン分け) ---
logger.info("--- 2. クラスタリングを開始します ---")
# 正しい列名 'population' と 'conv_store' を使用
# そのまま使うと人口の影響が大きすぎるため、対数変換してスケールを調整
df_cluster = df_analysis[['population', 'conv_store']].copy()
df_cluster['log_population'] = np.log(df_cluster['population'])
df_cluster['log_conv_store'] = np.log(df_cluster['conv_store'] + 1) # 0を避けるため+1

# k-means法で4つのクラスタに分類
kmeans = KMeans(n_clusters=4, random_state=0, n_init=10)
clusters = kmeans.fit_predict(df_cluster[['log_population', 'log_conv_store']])
df_analysis['cluster'] = clusters

logger.info("各市区町村がどのクラスタに分類されたかを追加しました。")
logger.info(df_analysis.head())

# クラスタリングの結果を可視化
plt.figure(figsize=(10, 8))
scatter = plt.scatter(df_analysis['population'], df_analysis['conv_store'], c=df_analysis['cluster'], cmap='viridis', alpha=0.7)
plt.xscale('log') # 人口のスケールが大きいため対数軸にする
plt.yscale('log') # コンビニ数も対数軸にする
plt.title('市区町村のクラスタリング分析')
plt.xlabel('市区町村の人口 (population・対数軸)')
plt.ylabel('コンビニ店舗数 (conv_store・対数軸)')
plt.legend(handles=scatter.legend_elements()[0], labels=['クラスタ0', 'クラスタ1', 'クラスタ2', 'クラスタ3'])
plt.grid(True, which="both", ls="--")
plt.savefig('data/pictures/clustering_analysis_final.png', dpi=300) # 画像として保存
logger.info("クラスタリング分析のグラフを 'clustering_analysis_final.png' として保存しました。")

# 各クラスタの特徴を確認
logger.info("--- 各クラスタの平均値 ---")
cluster_summary = df_analysis.groupby('cluster')[['population', 'conv_store']].mean()
logger.info(cluster_summary)

logger.info("分析が完了しました。")