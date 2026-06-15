import os
import random
import argparse
import numpy as np
import yaml
from scipy import stats

def load_config(config_path):
    """YAML設定ファイルを読み込む"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def parse_args():
    """コマンドライン引数を解析し、YAML設定ファイルをベースに上書きする"""
    parser = argparse.ArgumentParser(description="AB Test Simulation Framework")
    parser.add_argument("--config", type=str, default="configs/default.yaml", help="Path to config file")
    parser.add_argument("--scenario", type=str, choices=["baseline", "correlated", "imbalanced"], help="Scenario to run")
    parser.add_argument("--n_trials", type=int, help="Number of trials N")
    parser.add_argument("--n_users", type=int, help="Total number of users")
    parser.add_argument("--sessions_per_user", type=int, help="Average sessions per user")
    parser.add_argument("--split_ratio", type=float, help="Split ratio of group B (imbalanced scenario)")
    parser.add_argument("--rho", type=float, help="Correlation coefficient rho (correlated scenario)")
    parser.add_argument("--cvr_concentration", type=float, help="Beta distribution concentration parameter for CVR dispersion")
    parser.add_argument("--repeat_multiplier", type=float, help="CVR multiplier for repeated visits")
    parser.add_argument("--base_rate", type=float, help="Base conversion rate (Group A)")
    parser.add_argument("--relative_uplift", type=float, help="Relative CVR uplift for Group B")
    parser.add_argument("--alpha", type=float, help="Significance level alpha")
    parser.add_argument("--bootstrap_iter", type=int, help="Bootstrap iteration count")
    parser.add_argument("--seed", type=int, help="Random seed")
    parser.add_argument("--output_dir", type=str, help="Output directory")
    parser.add_argument("--run_name", type=str, help="Name of the subdirectory for output files")
    # power_calibratedシナリオ用のオプション引数
    parser.add_argument("--mde", type=float, help="Minimum Detectable Effect（既知の介入改善幅。例: 0.2 = 20%%）")
    parser.add_argument("--target_power", type=float, help="目標検出力（例: 0.8 = 80%%）")
    parser.add_argument("--n_pre_users", type=int, help="事前観測フェーズのユーザー数（power_calibratedシナリオ用）")
    parser.add_argument("--one_sided", action="store_true", help="片側検定を使用するフラグ（power_calibratedシナリオ用）")

    args = parser.parse_args()

    # configの読み込み
    config = load_config(args.config)

    # 引数による上書き（通常の引数）
    for key, val in vars(args).items():
        if key == "one_sided":
            continue  # store_trueフラグは個別処理
        if val is not None and key != "config":
            config[key] = val

    # one_sidedフラグの処理（store_trueはデフォルトがFalseのため個別処理）
    if args.one_sided:
        config["one_sided"] = True
    elif "one_sided" not in config:
        config["one_sided"] = False

    return config

def set_seed(seed):
    """乱数シードの設定"""
    random.seed(seed)
    np.random.seed(seed)

def ensure_dir(path):
    """ディレクトリが存在しない場合は作成する"""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def compute_n_users_z_test(p_a_session, mde, sessions_per_user, alpha=0.05, target_power=0.8, one_sided=True):
    """
    Z検定の独立性仮定（セッション単位）に基づくサンプル数計算。

    各セッションを独立した試行として扱い、標準公式で必要セッション数 n_session を算出後、
    sessions_per_user で割ってユーザー総数に換算する。
    この換算によって「情報量の水増し」が発生する。

    Returns:
        (n_users_total, n_sessions_per_group): ユーザー総数と1群あたり必要セッション数
    """
    p_b = min(p_a_session * (1.0 + mde), 1.0)
    z_alpha = stats.norm.ppf(1 - alpha) if one_sided else stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(target_power)
    p_pool = (p_a_session + p_b) / 2.0
    n_sessions_per_group = (
        (z_alpha * np.sqrt(2 * p_pool * (1 - p_pool)) +
         z_beta * np.sqrt(p_a_session * (1 - p_a_session) + p_b * (1 - p_b))) /
        abs(p_b - p_a_session)
    ) ** 2
    n_sessions_per_group = int(np.ceil(n_sessions_per_group))
    n_users_total = int(np.ceil(n_sessions_per_group * 2 / sessions_per_user))
    return n_users_total, n_sessions_per_group

def compute_n_users_bootstrap(p_a_user, var_user_cvr, mde, alpha=0.05, target_power=0.8, one_sided=True):
    """
    Bootstrapの仮定（ユーザー単位）に基づくサンプル数計算。

    事前観測データのユーザーレベルCVR分散を使用し、ユーザーを直接の標本単位とする。
    ユーザー間の相関構造を正しく反映した分散を用いるため、Z検定より多くのユーザーが必要となる。

    Returns:
        n_users_total: ユーザー総数
    """
    z_alpha = stats.norm.ppf(1 - alpha) if one_sided else stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(target_power)
    delta = p_a_user * mde
    if abs(delta) < 1e-10 or var_user_cvr < 1e-10:
        return 0
    n_users_per_group = (z_alpha + z_beta) ** 2 * 2 * var_user_cvr / (delta ** 2)
    return int(np.ceil(n_users_per_group * 2))
