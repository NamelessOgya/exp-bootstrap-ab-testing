import os
import json
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from utils import parse_args, set_seed, ensure_dir, compute_n_users_z_test, compute_n_users_bootstrap
from scenarios.correlated import generate_correlated_data
from scenarios.imbalanced import generate_imbalanced_data
from scenarios.pre_experiment import generate_pre_experiment_data
from tests.z_test import run_z_test
from tests.bootstrap_test import run_bootstrap_test

def main():
    # 1. パラメータの読み込み
    config = parse_args()
    
    # 乱数シードの設定
    set_seed(config["seed"])
    
    # シナリオごとの特殊パラメータ調整
    scenario = config["scenario"]
    if scenario == "baseline":
        # baselineでは偏りやリピート変動を無効化する
        config["cvr_concentration"] = 100000.0  # ほぼ一様
        config["repeat_multiplier"] = 1.0       # 変化なし
        config["split_ratio"] = 0.5             # 等分割
    elif scenario == "correlated":
        config["split_ratio"] = 0.5             # 等分割
        
    print(f"=== Starting AB Test Simulation ===")
    print(f"Scenario: {scenario}")
    print(f"N Trials (N): {config['n_trials']}")
    print(f"Sessions per User: {config['sessions_per_user']}")
    print(f"Base CVR: {config['base_rate']}")
    print(f"Relative Uplift: {config['relative_uplift']}")
    print(f"cvr_concentration: {config['cvr_concentration']}")
    print(f"repeat_multiplier: {config['repeat_multiplier']}")
    if config.get("mde") is not None:
        print(f"[power_calibrated] MDE: {config['mde']}, Target Power: {config.get('target_power', 0.8)}, "
              f"n_pre_users: {config.get('n_pre_users', 500)}, one_sided: {config.get('one_sided', True)}")
    else:
        print(f"Users (n_users): {config['n_users']}")
    print(f"====================================")
    
    pvals_z = []
    pvals_bs = []
    cvr_a_list = []
    cvr_b_list = []
    n_users_z_list = []   # power_calibrated: 各試行で計算されたZ検定必要ユーザー数
    n_users_bs_list = []  # power_calibrated: 各試行で計算されたBootstrap必要ユーザー数

    use_power_calibrated = config.get("mde") is not None
    sample_size_logged = False  # 最初の試行でのみサンプル数をログ出力する

    last_user_profiles = None
    # N回のシミュレーションループ
    for trial in range(1, config["n_trials"] + 1):
        if trial % 100 == 0 or trial == 1:
            print(f"Running trial {trial}/{config['n_trials']}...")

        is_last_trial = (trial == config["n_trials"])

        if use_power_calibrated:
            # ----------------------------------------------------------------
            # power_calibratedフロー
            # STEP 1: 事前観測 ─ 同一の相関構造でデータを生成し、CVR・分散を観測
            # ----------------------------------------------------------------
            n_pre_users = config.get("n_pre_users", 500)
            mde = config["mde"]
            target_power = config.get("target_power", 0.8)
            one_sided = config.get("one_sided", True)

            p_a_session, p_a_user, var_user_cvr = generate_pre_experiment_data(config, n_pre_users)

            # ----------------------------------------------------------------
            # STEP 2a: Z検定用サンプル数設計（セッション独立仮定）
            #   n_sessions_per_group を計算 → n_users_z = ceil(n_sessions × 2 / spu)
            # ----------------------------------------------------------------
            n_users_z, n_sess_per_group = compute_n_users_z_test(
                p_a_session, mde, config["sessions_per_user"],
                config["alpha"], target_power, one_sided
            )

            # ----------------------------------------------------------------
            # STEP 2b: Bootstrap用サンプル数設計（ユーザー独立仮定）
            #   ユーザーレベルCVR分散を使い、n_users_bs を直接計算
            # ----------------------------------------------------------------
            n_users_bs = compute_n_users_bootstrap(
                p_a_user, var_user_cvr, mde,
                config["alpha"], target_power, one_sided
            )

            # 最初の試行でサンプル数計算結果をログ出力
            if not sample_size_logged:
                print(f"--- [Sample Size Design: power_calibrated] ---")
                print(f"  Pre-exp CVR (session-level):  p_A_session = {p_a_session:.4f}")
                print(f"  Pre-exp CVR (user-level):     p_A_user    = {p_a_user:.4f}")
                print(f"  Pre-exp user CVR variance:    var_user    = {var_user_cvr:.6f}")
                print(f"  Z-Test  (sessions independent): n_sessions/group={n_sess_per_group}, n_users_z={n_users_z}")
                print(f"  Bootstrap (users independent):  n_users_bs={n_users_bs}")
                print(f"----------------------------------------------")
                sample_size_logged = True

            # 各試行のサンプル数を記録
            n_users_z_list.append(n_users_z)
            n_users_bs_list.append(n_users_bs)

            # ----------------------------------------------------------------
            # STEP 3a: Z検定用実験データ生成 & 片側Z検定実施
            # ----------------------------------------------------------------
            config_z = {**config, "n_users": n_users_z}
            user_profiles_z, session_logs_z = generate_correlated_data(config_z)
            p_z, cvr_a, cvr_b = run_z_test(session_logs_z, one_sided=one_sided)

            # ----------------------------------------------------------------
            # STEP 3b: Bootstrap用実験データ生成 & 片側Bootstrap実施
            # ----------------------------------------------------------------
            config_bs = {**config, "n_users": n_users_bs}
            user_profiles_bs, session_logs_bs = generate_correlated_data(config_bs)

            if is_last_trial:
                last_user_profiles = user_profiles_bs
                p_bs, theta_stars, theta_obs, se_theory = run_bootstrap_test(
                    session_logs_bs, bootstrap_iter=config["bootstrap_iter"],
                    return_dist=True, one_sided=one_sided
                )
            else:
                p_bs = run_bootstrap_test(
                    session_logs_bs, bootstrap_iter=config["bootstrap_iter"],
                    one_sided=one_sided
                )
        else:
            # ----------------------------------------------------------------
            # 標準フロー（baseline / correlated / imbalanced）
            # ----------------------------------------------------------------
            if scenario == "imbalanced":
                user_profiles, session_logs = generate_imbalanced_data(config)
            else:
                # baseline および correlated は correlated用のロジックで対応
                user_profiles, session_logs = generate_correlated_data(config)

            p_z, cvr_a, cvr_b = run_z_test(session_logs)

            if is_last_trial:
                last_user_profiles = user_profiles
                p_bs, theta_stars, theta_obs, se_theory = run_bootstrap_test(
                    session_logs, bootstrap_iter=config["bootstrap_iter"], return_dist=True
                )
            else:
                p_bs = run_bootstrap_test(session_logs, bootstrap_iter=config["bootstrap_iter"])

        pvals_z.append(p_z)
        cvr_a_list.append(cvr_a)
        cvr_b_list.append(cvr_b)
        pvals_bs.append(p_bs)
        
    pvals_z = np.array(pvals_z)
    pvals_bs = np.array(pvals_bs)
    
    # 評価指標の算出
    alpha = config["alpha"]
    rejection_rate_z = np.mean(pvals_z <= alpha)
    rejection_rate_bs = np.mean(pvals_bs <= alpha)
    
    metric_name = "Power" if config["relative_uplift"] != 0.0 else "Type I Error Rate"
    
    print(f"--- Results ---")
    print(f"Z-Test {metric_name}: {rejection_rate_z:.4f}")
    print(f"Bootstrap-Test {metric_name}: {rejection_rate_bs:.4f}")
    
    # 結果保存用ディレクトリの作成
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = config.get("run_name")
    if not run_name:
        run_name = f"{scenario}_{timestamp}"
        
    run_dir = os.path.join(config["output_dir"], run_name)
    fig_dir = os.path.join(run_dir, "figures")
    ensure_dir(fig_dir)
    
    # sample_sizes.csv の保存（power_calibrated のみ）
    if use_power_calibrated and n_users_z_list:
        pd.DataFrame({
            "trial":      range(1, len(n_users_z_list) + 1),
            "n_users_z":  n_users_z_list,
            "n_users_bs": n_users_bs_list,
        }).to_csv(os.path.join(run_dir, "sample_sizes.csv"), index=False)

    # CSVの保存
    pd.DataFrame({"trial": range(1, len(pvals_z) + 1), "p_value": pvals_z, "cvr_a": cvr_a_list, "cvr_b": cvr_b_list}).to_csv(
        os.path.join(run_dir, "pvalues_ztest.csv"), index=False
    )
    pd.DataFrame({"trial": range(1, len(pvals_bs) + 1), "p_value": pvals_bs}).to_csv(
        os.path.join(run_dir, "pvalues_bootstrap.csv"), index=False
    )
    
    # summary.jsonの保存
    summary = {
        "timestamp": timestamp,
        "config": config,
        "metrics": {
            "metric_type": metric_name,
            "z_test_rejection_rate": float(rejection_rate_z),
            "bootstrap_rejection_rate": float(rejection_rate_bs),
            "mean_cvr_a": float(np.mean(cvr_a_list)),
            "mean_cvr_b": float(np.mean(cvr_b_list))
        }
    }
    # power_calibrated の場合、サンプル数情報を追記
    if use_power_calibrated and n_users_z_list:
        summary["metrics"]["mean_n_users_z"]  = float(np.mean(n_users_z_list))
        summary["metrics"]["std_n_users_z"]   = float(np.std(n_users_z_list))
        summary["metrics"]["mean_n_users_bs"] = float(np.mean(n_users_bs_list))
        summary["metrics"]["std_n_users_bs"]  = float(np.std(n_users_bs_list))
        print(f"  Mean n_users_z : {np.mean(n_users_z_list):.1f}  (std={np.std(n_users_z_list):.1f})")
        print(f"  Mean n_users_bs: {np.mean(n_users_bs_list):.1f}  (std={np.std(n_users_bs_list):.1f})")
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)
        
    # 可視化 (pvalue_distribution.png)
    plt.figure(figsize=(12, 5))
    
    # ヒストグラム
    plt.subplot(1, 2, 1)
    sns.histplot(pvals_z, bins=20, kde=False, color="blue", alpha=0.5, label="Z-Test", stat="probability")
    sns.histplot(pvals_bs, bins=20, kde=False, color="orange", alpha=0.5, label="Bootstrap", stat="probability")
    plt.axhline(1/20, color="red", linestyle="--", label="Uniform (Ideal H0)")
    plt.title("p-value Distribution")
    plt.xlabel("p-value")
    plt.ylabel("Probability")
    plt.legend()
    
    # 累積分布関数 (CDF)
    plt.subplot(1, 2, 2)
    plt.plot(np.sort(pvals_z), np.linspace(0, 1, len(pvals_z)), label="Z-Test", color="blue")
    plt.plot(np.sort(pvals_bs), np.linspace(0, 1, len(pvals_bs)), label="Bootstrap", color="orange")
    plt.plot([0, 1], [0, 1], color="red", linestyle="--", label="Ideal Uniform")
    plt.title("p-value CDF")
    plt.xlabel("p-value")
    plt.ylabel("Cumulative Probability")
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "pvalue_distribution.png"), dpi=150)
    plt.close()
    
    # 棄却率の比較プロット (power_curve.png)
    plt.figure(figsize=(6, 5))
    methods = ["Z-Test", "Bootstrap-Test"]
    rates = [rejection_rate_z, rejection_rate_bs]
    colors = ["blue", "orange"]
    
    sns.barplot(x=methods, y=rates, hue=methods, palette=colors, legend=False)
    plt.axhline(alpha, color="red", linestyle="--", label=f"Significance Level alpha ({alpha})")
    plt.ylabel("Rejection Rate (Rejections / N)")
    plt.title(f"Rejection Rate Comparison ({metric_name})")
    plt.ylim(0, 1.05)
    plt.legend()
    
    plt.savefig(os.path.join(fig_dir, "power_curve.png"), dpi=150)
    plt.close()
    
    # 最後の試行における比率の差の分布比較プロット (bootstrap_vs_theory.png)
    plt.figure(figsize=(8, 6))
    
    # 1. Bootstrap経験分布
    sns.histplot(theta_stars, kde=True, color="orange", stat="density", label="Bootstrap Distribution\n(Reflects User Correlation)", alpha=0.4)
    
    # 2. Z検定が仮定する理論正規分布 (実測値の差 theta_obs を平均、se_theory を標準偏差とする)
    x_min, x_max = plt.xlim()
    padding = max(se_theory * 4, (x_max - x_min) * 0.1)
    plot_x = np.linspace(min(x_min, theta_obs - padding), max(x_max, theta_obs + padding), 300)
    
    y_normal = (1 / (se_theory * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((plot_x - theta_obs) / se_theory)**2)
    plt.plot(plot_x, y_normal, color="blue", linewidth=2.5, label="Z-Test Theoretical Distribution\n(Assumes Session Independence)")
    
    # 実測値の差とゼロライン
    plt.axvline(theta_obs, color="red", linestyle="--", linewidth=1.5, label=f"Observed Difference ({theta_obs:.4f})")
    plt.axvline(0.0, color="gray", linestyle="-", linewidth=1, label="H0 (No Difference)")
    
    plt.title(f"Sampling Distribution of CVR Difference ({scenario.capitalize()})")
    plt.xlabel("Difference in CVR (p_B - p_A)")
    plt.ylabel("Density")
    plt.legend()
    plt.tight_layout()
    
    plt.savefig(os.path.join(fig_dir, "bootstrap_vs_theory.png"), dpi=150)
    plt.close()
    
    # ユーザー固有CVRの分布プロット (user_cvr_distribution.png)
    if last_user_profiles is not None:
        plt.figure(figsize=(8, 6))
        sns.histplot(data=last_user_profiles, x="base_cvr", hue="group", kde=True, bins=30, multiple="dodge", palette={"A": "blue", "B": "orange"})
        plt.title(f"User Base CVR Distribution ({scenario.capitalize()})")
        plt.xlabel("User Base CVR")
        plt.ylabel("Count")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, "user_cvr_distribution.png"), dpi=150)
        plt.close()
        print(f"Created: user_cvr_distribution.png in {fig_dir}")
        
    print(f"Results saved to: {run_dir}")

if __name__ == "__main__":
    main()
