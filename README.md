# exp-bootstrap-ab-testing

**母比率の差の検定** をテーマにしたABテストシミュレーション実験リポジトリです。  
Bootstrap検定と通常の母比率の差の検定を、複数の実験条件下で比較・評価します。

---

## 概要

ABテストにおける統計的検定手法の妥当性を、シミュレーションによって検証します。  
特に以下の2つの検定手法を比較します。

| 検定手法 | 概要 |
|---|---|
| **通常の母比率の差の検定** | `z`検定による漸近理論に基づいた検定 |
| **Bootstrap検定** | リサンプリングによるノンパラメトリックな検定 |

### 検証する実験条件

| 条件 | 説明 |
|---|---|
| **試行ごとに相関がある場合** | ユーザー内に繰り返し観測があり、観測間に正の相関が存在するシナリオ（例：同一ユーザーの複数セッション） |
| **ユーザー数に差がある場合** | コントロール群とトリートメント群でサンプルサイズが異なるシナリオ（不均等割り付け） |

---

## 実験インターフェース

実験は以下の流れで `N` 回繰り返します。

```
for i in range(N):
    1. ユーザープロファイルを生成
       （cvr_concentration を基に、各ユーザーの基本コンバージョン確率を生成）
    2. ユーザーを A群 / B群 にランダム分割 (AB splitting)
    3. 分割されたデータとパラメータ（repeat_multiplier 等）を基に、コンバージョン（0/1）をシミュレーション
    4. 通常の母比率の差の検定 → p値を記録
    5. Bootstrap検定 → p値を記録

→ N回の検定結果を集計し、第一種過誤率・検出力などを評価
```

パラメータはYAML設定ファイル、またはコマンドライン引数で指定可能です。

---

## 設定ファイル (YAML)

シミュレーションのパラメータは、YAML形式の設定ファイルで管理・指定することができます。

### 設定ファイルの例 (`configs/default.yaml`)

```yaml
n_trials: 1000             # ABテストシミュレーションの繰り返し回数 N
scenario: "correlated"     # 実験条件 (correlated / imbalanced / baseline)
n_users: 200               # 実験に使用する総ユーザー数
split_ratio: 0.5           # A群:B群の割り付け比率 (imbalanced時に有効)
rho: 0.3                   # 観測間の相関係数 (correlated時に有効)
cvr_concentration: 10000.0  # ユーザー間CVRの集中度 (値が小さいほど偏りが大きく、10000等でほぼ一様)
repeat_multiplier: 1.0     # 2回目以降のCVR倍率 (1.0で変化なし、1.5で1.5倍に上昇)
base_rate: 0.1             # ベースコンバージョン率 (A群)
relative_uplift: 0.0       # 手法Bの手法Aに対する相対的な改善率 (0.0のとき帰無仮説が真)
alpha: 0.05                # 有意水準
bootstrap_iter: 1000       # Bootstrapリサンプリング回数
seed: 42                   # 乱数シード
output_dir: "./results"    # 結果の出力先ディレクトリ
```

---

## ディレクトリ構成（予定）

```
exp-bootstrap-ab-testing/
├── README.md
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── configs/
│   └── default.yaml           # 実験設定ファイル (YAML)
├── src/
│   ├── simulation.py          # シミュレーション本体（N回ループ）
│   ├── tests/
│   │   ├── z_test.py          # 通常の母比率の差の検定
│   │   └── bootstrap_test.py  # Bootstrap検定
│   ├── scenarios/
│   │   ├── correlated.py      # 観測間に相関がある場合
│   │   └── imbalanced.py      # ユーザー数に差がある場合
│   └── utils.py               # 共通ユーティリティ
├── results/                   # 実験結果の出力先
└── scripts/
    └── run_experiment.sh      # 実験実行スクリプト
```

---

## 環境構築

> **本実験はすべてDockerコンテナ上で実行します。**  
> ローカル環境へのPythonパッケージの直接インストールは行いません。

### 前提条件

- Docker >= 24.0
- Docker Compose >= 2.0

### セットアップ

```bash
# リポジトリのクローン
git clone https://github.com/NamelessOgya/exp-bootstrap-ab-testing.git
cd exp-bootstrap-ab-testing

# Dockerイメージのビルド
docker compose build
```

---

## 実験の実行

### 設定ファイルを使用した実行方法

```bash
# YAML設定ファイルを指定して実行
docker compose run --rm simulation --config configs/default.yaml
```

### コマンドライン引数でパラメータを上書きして実行

YAML設定ファイルをベースにしつつ、特定のパラメータのみコマンドライン引数で上書きして実行することも可能です。

```bash
# 特定のシナリオやパラメータのみを上書きして実行
docker compose run --rm simulation \
  --config configs/default.yaml \
  --scenario imbalanced \
  --split_ratio 0.8
```

### 全条件の一括実行

```bash
docker compose run --rm simulation bash scripts/run_experiment.sh
```

---

## 出力と評価指標

実験結果は `results/` ディレクトリに保存されます。

### 出力ファイル

```
results/
├── {scenario}_{timestamp}/
│   ├── summary.json           # 集計指標（第一種過誤率・検出力など）
│   ├── pvalues_ztest.csv      # 各試行のz検定p値
│   ├── pvalues_bootstrap.csv  # 各試行のBootstrap検定p値
│   └── figures/
│       ├── pvalue_distribution.png   # p値の分布
│       └── power_curve.png           # 検出力曲線
```

### 評価指標

| 指標 | 説明 |
|---|---|
| **第一種過誤率 (α error)** | 帰無仮説が真のとき、誤って棄却する割合（`relative_uplift=0.0` で測定） |
| **検出力 (Power)** | 帰無仮説が偽のとき、正しく棄却できる割合 |
| **p値の分布** | 有効な検定ならば一様分布 `Uniform(0,1)` に従うことを確認 |

---

## 実験設計の詳細

### 条件1：試行ごとに相関がある場合（`correlated`）

同一ユーザーに対して複数回の試行（例：ページ訪問）があり、各ユーザーの観測値間に相関 ρ が存在するシナリオです。

- **生成モデル**：ベータ-二項モデルなどを用いて、ユーザー効果（ランダム効果）を導入。具体的には、ベータ分布の集中度パラメータ（`cvr_concentration`）によるユーザーごとのCVRの偏りに加え、2回目以降のアクセスでCVRを変動させるパラメータ（`repeat_multiplier`）を導入して動的な行動をモデル化します。
- **検証観点**：観測間の相関を無視した通常のz検定が第一種過誤率を過剰に膨らませることを確認し、Bootstrapが頑健であるかを検証する

### 条件2：ユーザー数に差がある場合（`imbalanced`）

A群とB群のサンプルサイズが大きく異なるシナリオです（例：A群80%・B群20%の割り付け）。

- **検証観点**：不均等割り付け下での両手法の検出力と第一種過誤率を比較し、サンプルサイズ不均衡に対する頑健性を評価する

---

## 技術スタック

| カテゴリ | ライブラリ |
|---|---|
| 統計検定 | `scipy`, `statsmodels` |
| Bootstrap処理 | `numpy` |
| 可視化 | `matplotlib`, `seaborn` |
| データ操作 | `pandas` |
| 実験管理 | `argparse`, `PyYAML`, `json` |
| 環境 | `Docker`, `Docker Compose` |

---

## ライセンス

MIT License
