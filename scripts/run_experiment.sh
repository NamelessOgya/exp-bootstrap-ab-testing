#!/bin/bash

# エラーが発生したら即座に終了する
set -e

# デフォルトパラメータ
N_TRIALS=""
BOOTSTRAP_ITER=""

# --test 引数の処理
if [ "$1" = "--test" ]; then
    echo "=== Running in TEST MODE (reduced trials) ==="
    N_TRIALS="--n_trials 5"
    BOOTSTRAP_ITER="--bootstrap_iter 50"
fi

# 一括実行用のタイムスタンプを生成
BATCH_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="./results/batch_${BATCH_TIMESTAMP}"

echo "Starting batch experiments..."
echo "All results will be saved to: ${OUTPUT_DIR}"

# バッチフォルダを作成し、実験設定ファイルをコピー
mkdir -p "${OUTPUT_DIR}"
cp configs/default.yaml "${OUTPUT_DIR}/experiment_config.yaml"
echo "Saved experiment config to: ${OUTPUT_DIR}/experiment_config.yaml"

# -------------------------------------------------------
# 1〜2. Baseline + Power-Calibrated フロー
# IIDデータ（cvr_concentration=100000, repeat_multiplier=1.0）で
# 事前観測からサンプル数を設計する。Z検定の仮定が正しい場合の挙動を確認する。
# -------------------------------------------------------

# 1. Baseline (power_calibrated) - Type I Error
echo "----------------------------------------"
echo "Running Baseline (Power-Calibrated): Type I Error"
python src/simulation.py \
  --scenario baseline \
  --relative_uplift 0.0 \
  --mde 0.2 \
  --target_power 0.8 \
  --n_pre_users 500 \
  --one_sided \
  --output_dir "$OUTPUT_DIR" \
  --run_name "baseline_pc_type1_error" \
  $N_TRIALS $BOOTSTRAP_ITER

# 2. Baseline (power_calibrated) - Power
echo "----------------------------------------"
echo "Running Baseline (Power-Calibrated): Power"
python src/simulation.py \
  --scenario baseline \
  --relative_uplift 0.2 \
  --mde 0.2 \
  --target_power 0.8 \
  --n_pre_users 500 \
  --one_sided \
  --output_dir "$OUTPUT_DIR" \
  --run_name "baseline_pc_power" \
  $N_TRIALS $BOOTSTRAP_ITER

# -------------------------------------------------------
# 3〜4. Power-Calibrated フロー（相関ありデータ）
# ユーザー間CVR偏りあり（cvr_concentration=2.0）・複数回訪問あり（repeat_multiplier=1.5）で
# 事前観測からサンプル数を設計する。Z検定の仮定が誤っている場合の挙動を確認する。
# -------------------------------------------------------

# 3. Power-Calibrated - Type I Error
echo "----------------------------------------"
echo "Running Power-Calibrated Scenario: Type I Error"
python src/simulation.py \
  --scenario correlated \
  --relative_uplift 0.0 \
  --cvr_concentration 2.0 \
  --repeat_multiplier 1.5 \
  --mde 0.2 \
  --target_power 0.8 \
  --n_pre_users 500 \
  --one_sided \
  --output_dir "$OUTPUT_DIR" \
  --run_name "power_calibrated_type1_error" \
  $N_TRIALS $BOOTSTRAP_ITER

# 4. Power-Calibrated - Power
echo "----------------------------------------"
echo "Running Power-Calibrated Scenario: Power"
python src/simulation.py \
  --scenario correlated \
  --relative_uplift 0.2 \
  --cvr_concentration 2.0 \
  --repeat_multiplier 1.5 \
  --mde 0.2 \
  --target_power 0.8 \
  --n_pre_users 500 \
  --one_sided \
  --output_dir "$OUTPUT_DIR" \
  --run_name "power_calibrated_power" \
  $N_TRIALS $BOOTSTRAP_ITER

# -------------------------------------------------------
# 7〜10. CVR集中度スイープ（Type I Error のみ）
# cvr_concentration を変化させて第一種過誤率への影響を可視化する
# 値が小さいほどユーザー間CVRの偏りが大きく（相関が強く）、Z検定が崩れやすい
# -------------------------------------------------------

# 7. CVR Sweep - cvr_concentration=2.0（最も分散が大きい）
echo "----------------------------------------"
echo "Running CVR Concentration Sweep: cvr_concentration=2.0"
python src/simulation.py --scenario correlated --relative_uplift 0.0 --cvr_concentration 2.0 --repeat_multiplier 1.5 --output_dir "$OUTPUT_DIR" --run_name "cvr_sweep_2" $N_TRIALS $BOOTSTRAP_ITER

# 8. CVR Sweep - cvr_concentration=10.0
echo "----------------------------------------"
echo "Running CVR Concentration Sweep: cvr_concentration=10.0"
python src/simulation.py --scenario correlated --relative_uplift 0.0 --cvr_concentration 10.0 --repeat_multiplier 1.5 --output_dir "$OUTPUT_DIR" --run_name "cvr_sweep_10" $N_TRIALS $BOOTSTRAP_ITER

# 9. CVR Sweep - cvr_concentration=100.0
echo "----------------------------------------"
echo "Running CVR Concentration Sweep: cvr_concentration=100.0"
python src/simulation.py --scenario correlated --relative_uplift 0.0 --cvr_concentration 100.0 --repeat_multiplier 1.5 --output_dir "$OUTPUT_DIR" --run_name "cvr_sweep_100" $N_TRIALS $BOOTSTRAP_ITER

# 10. CVR Sweep - cvr_concentration=1000.0（ほぼ均一CVR、baselineに近い）
echo "----------------------------------------"
echo "Running CVR Concentration Sweep: cvr_concentration=1000.0"
python src/simulation.py --scenario correlated --relative_uplift 0.0 --cvr_concentration 1000.0 --repeat_multiplier 1.5 --output_dir "$OUTPUT_DIR" --run_name "cvr_sweep_1000" $N_TRIALS $BOOTSTRAP_ITER

# -------------------------------------------------------
# 11〜14. CVR集中度スイープ（Power / 第二種過誤確認）
# cvr_concentration を変化させて検出力（= 1 - 第二種過誤率）への影響を可視化する
# -------------------------------------------------------

# 11. CVR Sweep Power - cvr_concentration=2.0
echo "----------------------------------------"
echo "Running CVR Concentration Sweep Power: cvr_concentration=2.0"
python src/simulation.py --scenario correlated --relative_uplift 0.2 --cvr_concentration 2.0 --repeat_multiplier 1.5 --output_dir "$OUTPUT_DIR" --run_name "cvr_sweep_2_power" $N_TRIALS $BOOTSTRAP_ITER

# 12. CVR Sweep Power - cvr_concentration=10.0
echo "----------------------------------------"
echo "Running CVR Concentration Sweep Power: cvr_concentration=10.0"
python src/simulation.py --scenario correlated --relative_uplift 0.2 --cvr_concentration 10.0 --repeat_multiplier 1.5 --output_dir "$OUTPUT_DIR" --run_name "cvr_sweep_10_power" $N_TRIALS $BOOTSTRAP_ITER

# 13. CVR Sweep Power - cvr_concentration=100.0
echo "----------------------------------------"
echo "Running CVR Concentration Sweep Power: cvr_concentration=100.0"
python src/simulation.py --scenario correlated --relative_uplift 0.2 --cvr_concentration 100.0 --repeat_multiplier 1.5 --output_dir "$OUTPUT_DIR" --run_name "cvr_sweep_100_power" $N_TRIALS $BOOTSTRAP_ITER

# 14. CVR Sweep Power - cvr_concentration=1000.0
echo "----------------------------------------"
echo "Running CVR Concentration Sweep Power: cvr_concentration=1000.0"
python src/simulation.py --scenario correlated --relative_uplift 0.2 --cvr_concentration 1000.0 --repeat_multiplier 1.5 --output_dir "$OUTPUT_DIR" --run_name "cvr_sweep_1000_power" $N_TRIALS $BOOTSTRAP_ITER

# サマリーグラフの自動生成
python src/plot_summary.py --batch_dir "$OUTPUT_DIR"

echo "----------------------------------------"
echo "Batch experiments completed successfully!"
