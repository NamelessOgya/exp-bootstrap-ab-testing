import os
import json
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    parser = argparse.ArgumentParser(description="Create summary plots for batch experiment results")
    parser.add_argument("--batch_dir", type=str, required=True, help="Path to batch results directory")
    args = parser.parse_args()

    # -------------------------------------------------------
    # メインシナリオ（棒グラフ用）
    # 両シナリオとも「事前サンプルからサンプル数を設計」という条件を統一
    #   baseline (pc) : IIDデータ（相関なし）+ 事前サンプル設計
    #   power_calibrated: 相関ありデータ + 事前サンプル設計
    # -------------------------------------------------------
    cases = [
        {"dir": "baseline_pc_type1_error",       "scenario": "baseline\n(IID, pre-exp design)",        "metric_type": "Type I Error Rate"},
        {"dir": "baseline_pc_power",             "scenario": "baseline\n(IID, pre-exp design)",        "metric_type": "Power"},
        {"dir": "power_calibrated_type1_error",  "scenario": "power_calibrated\n(correlated, pre-exp design)", "metric_type": "Type I Error Rate"},
        {"dir": "power_calibrated_power",        "scenario": "power_calibrated\n(correlated, pre-exp design)", "metric_type": "Power"},
    ]

    # -------------------------------------------------------
    # CVR集中度スイープ（Type I Error用）
    # -------------------------------------------------------
    sweep_cases = [
        {"dir": "cvr_sweep_2",    "cvr_concentration": 2.0},
        {"dir": "cvr_sweep_10",   "cvr_concentration": 10.0},
        {"dir": "cvr_sweep_100",  "cvr_concentration": 100.0},
        {"dir": "cvr_sweep_1000", "cvr_concentration": 1000.0},
    ]

    # -------------------------------------------------------
    # CVR集中度スイープ（Power / 第二種過誤用）
    # -------------------------------------------------------
    sweep_power_cases = [
        {"dir": "cvr_sweep_2_power",    "cvr_concentration": 2.0},
        {"dir": "cvr_sweep_10_power",   "cvr_concentration": 10.0},
        {"dir": "cvr_sweep_100_power",  "cvr_concentration": 100.0},
        {"dir": "cvr_sweep_1000_power", "cvr_concentration": 1000.0},
    ]

    # -------------------------------------------------------
    # メインシナリオデータの読み込み
    # -------------------------------------------------------
    data = []
    alpha = 0.05

    for case in cases:
        summary_path = os.path.join(args.batch_dir, case["dir"], "summary.json")
        if not os.path.exists(summary_path):
            print(f"Warning: Summary file not found: {summary_path}")
            continue

        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

        alpha = summary.get("config", {}).get("alpha", 0.05)

        # Z-TestのCSV読み込み
        z_csv_path = os.path.join(args.batch_dir, case["dir"], "pvalues_ztest.csv")
        if os.path.exists(z_csv_path):
            df_z = pd.read_csv(z_csv_path)
            for _, row in df_z.iterrows():
                if pd.notna(row["p_value"]):
                    data.append({
                        "Scenario": case["scenario"],
                        "Metric": case["metric_type"],
                        "Method": "Z-Test",
                        "Rejected": 1 if row["p_value"] <= alpha else 0
                    })
        else:
            print(f"Warning: Z-Test CSV not found: {z_csv_path}")

        # Bootstrap-TestのCSV読み込み
        bs_csv_path = os.path.join(args.batch_dir, case["dir"], "pvalues_bootstrap.csv")
        if os.path.exists(bs_csv_path):
            df_bs = pd.read_csv(bs_csv_path)
            for _, row in df_bs.iterrows():
                if pd.notna(row["p_value"]):
                    data.append({
                        "Scenario": case["scenario"],
                        "Metric": case["metric_type"],
                        "Method": "Bootstrap-Test",
                        "Rejected": 1 if row["p_value"] <= alpha else 0
                    })
        else:
            print(f"Warning: Bootstrap-Test CSV not found: {bs_csv_path}")

    df = pd.DataFrame(data)

    # -------------------------------------------------------
    # CVRスイープデータの読み込み
    # -------------------------------------------------------
    sweep_data = []
    n_trials_ref = 1000  # 信頼区間用

    for sc in sweep_cases:
        summary_path = os.path.join(args.batch_dir, sc["dir"], "summary.json")
        if not os.path.exists(summary_path):
            print(f"Warning: Sweep summary not found: {summary_path}")
            continue

        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

        n_trials_ref = summary.get("config", {}).get("n_trials", 1000)
        alpha_sw = summary.get("config", {}).get("alpha", 0.05)

        # Z-TestのCSVから棄却率と95%CI
        z_csv = os.path.join(args.batch_dir, sc["dir"], "pvalues_ztest.csv")
        if os.path.exists(z_csv):
            pvals = pd.read_csv(z_csv)["p_value"].dropna()
            rejected = (pvals <= alpha_sw).astype(int)
            n = len(rejected)
            rate = rejected.mean()
            se = np.sqrt(rate * (1 - rate) / n) if n > 0 else 0
            sweep_data.append({
                "cvr_concentration": sc["cvr_concentration"],
                "Method": "Z-Test",
                "rate": rate,
                "ci_low": max(0, rate - 1.96 * se),
                "ci_high": min(1, rate + 1.96 * se),
            })

        # Bootstrap-TestのCSVから棄却率と95%CI
        bs_csv = os.path.join(args.batch_dir, sc["dir"], "pvalues_bootstrap.csv")
        if os.path.exists(bs_csv):
            pvals = pd.read_csv(bs_csv)["p_value"].dropna()
            rejected = (pvals <= alpha_sw).astype(int)
            n = len(rejected)
            rate = rejected.mean()
            se = np.sqrt(rate * (1 - rate) / n) if n > 0 else 0
            sweep_data.append({
                "cvr_concentration": sc["cvr_concentration"],
                "Method": "Bootstrap-Test",
                "rate": rate,
                "ci_low": max(0, rate - 1.96 * se),
                "ci_high": min(1, rate + 1.96 * se),
            })

    df_sweep = pd.DataFrame(sweep_data)

    # -------------------------------------------------------
    # CVRスイープのPowerデータの読み込み
    # -------------------------------------------------------
    sweep_power_data = []

    for sc in sweep_power_cases:
        summary_path = os.path.join(args.batch_dir, sc["dir"], "summary.json")
        if not os.path.exists(summary_path):
            print(f"Warning: Sweep Power summary not found: {summary_path}")
            continue

        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        alpha_sw = summary.get("config", {}).get("alpha", 0.05)

        # Z-Test Power
        z_csv = os.path.join(args.batch_dir, sc["dir"], "pvalues_ztest.csv")
        if os.path.exists(z_csv):
            pvals = pd.read_csv(z_csv)["p_value"].dropna()
            rejected = (pvals <= alpha_sw).astype(int)
            n = len(rejected)
            power_rate = rejected.mean()
            type2 = 1.0 - power_rate
            se = np.sqrt(power_rate * (1 - power_rate) / n) if n > 0 else 0
            sweep_power_data.append({
                "cvr_concentration": sc["cvr_concentration"],
                "Method": "Z-Test",
                "power": power_rate,
                "type2": type2,
                "ci_low_power": max(0, power_rate - 1.96 * se),
                "ci_high_power": min(1, power_rate + 1.96 * se),
                "ci_low_type2": max(0, type2 - 1.96 * se),
                "ci_high_type2": min(1, type2 + 1.96 * se),
            })

        # Bootstrap-Test Power
        bs_csv = os.path.join(args.batch_dir, sc["dir"], "pvalues_bootstrap.csv")
        if os.path.exists(bs_csv):
            pvals = pd.read_csv(bs_csv)["p_value"].dropna()
            rejected = (pvals <= alpha_sw).astype(int)
            n = len(rejected)
            power_rate = rejected.mean()
            type2 = 1.0 - power_rate
            se = np.sqrt(power_rate * (1 - power_rate) / n) if n > 0 else 0
            sweep_power_data.append({
                "cvr_concentration": sc["cvr_concentration"],
                "Method": "Bootstrap-Test",
                "power": power_rate,
                "type2": type2,
                "ci_low_power": max(0, power_rate - 1.96 * se),
                "ci_high_power": min(1, power_rate + 1.96 * se),
                "ci_low_type2": max(0, type2 - 1.96 * se),
                "ci_high_type2": min(1, type2 + 1.96 * se),
            })

    df_sweep_power = pd.DataFrame(sweep_power_data)

    # -------------------------------------------------------
    # Figure 1: メインシナリオ比較（棒グラフ）
    # -------------------------------------------------------
    if not df.empty:
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # Type I Error Rate（左）
        df_err = df[df["Metric"] == "Type I Error Rate"]
        if not df_err.empty:
            sns.barplot(
                data=df_err, x="Scenario", y="Rejected", hue="Method",
                palette=["blue", "orange"], ax=axes[0],
                errorbar=("ci", 95), capsize=0.1
            )
            axes[0].axhline(alpha, color="red", linestyle="--", label=f"Significance Level α ({alpha})")
            axes[0].set_ylabel("Type I Error Rate (with 95% CI)")
            axes[0].set_xlabel("Scenario")
            axes[0].set_title("Type I Error Rate Comparison\n(Lower is Better, Ideal = 0.05)")
            max_rate = df_err.groupby(["Scenario", "Method"])["Rejected"].mean().max()
            axes[0].set_ylim(0, max(0.1, max_rate * 1.5))
            axes[0].legend()
            axes[0].grid(True, linestyle="--", alpha=0.5)
        else:
            axes[0].text(0.5, 0.5, "No Type I Error Data", ha="center", va="center")

        # Power（右）
        df_power = df[df["Metric"] == "Power"]
        if not df_power.empty:
            sns.barplot(
                data=df_power, x="Scenario", y="Rejected", hue="Method",
                palette=["blue", "orange"], ax=axes[1],
                errorbar=("ci", 95), capsize=0.1
            )
            axes[1].set_ylabel("Power (with 95% CI)")
            axes[1].set_xlabel("Scenario")
            axes[1].set_title("Power Comparison\n(Higher is Better)")
            axes[1].set_ylim(0, 1.05)
            axes[1].legend()
            axes[1].grid(True, linestyle="--", alpha=0.5)
        else:
            axes[1].text(0.5, 0.5, "No Power Data", ha="center", va="center")

        plt.suptitle(
            "Statistical Test Performance & Trade-off Comparison (Z-Test vs Bootstrap)",
            fontsize=14, y=1.01
        )
        plt.tight_layout()
        plt.savefig(os.path.join(args.batch_dir, "summary_comparison.png"), dpi=150, bbox_inches="tight")
        plt.close()
        print("Created: summary_comparison.png")
    else:
        print("No main scenario data found. Skipping summary_comparison.png.")

    # -------------------------------------------------------
    # Figure 2: CVR集中度スイープ（上段: Type I Error / 下段: Type II Error）
    # -------------------------------------------------------
    has_type1 = not df_sweep.empty
    has_type2 = "df_sweep_power" in dir() and not df_sweep_power.empty

    if has_type1 or has_type2:
        fig, axes = plt.subplots(2, 1, figsize=(9, 10), sharex=True)
        colors = {"Z-Test": "blue", "Bootstrap-Test": "orange"}

        # --- 上段: Type I Error Rate ---
        ax0 = axes[0]
        if has_type1:
            for method, grp in df_sweep.groupby("Method"):
                grp = grp.sort_values("cvr_concentration")
                ax0.plot(
                    grp["cvr_concentration"], grp["rate"],
                    marker="o", label=method, color=colors.get(method, "gray"), linewidth=2
                )
                ax0.fill_between(
                    grp["cvr_concentration"], grp["ci_low"], grp["ci_high"],
                    alpha=0.15, color=colors.get(method, "gray")
                )
        ax0.axhline(alpha, color="red", linestyle="--", linewidth=1.5,
                    label=f"Significance Level alpha ({alpha})")
        ax0.set_ylabel("Type I Error Rate (with 95% CI)", fontsize=11)
        ax0.set_title(
            "CVR Concentration vs Type I Error Rate\n"
            "(smaller cvr_concentration = more user CVR dispersion = Z-Test breaks down)",
            fontsize=11
        )
        ax0.set_ylim(0, None)
        ax0.legend(fontsize=10)
        ax0.grid(True, linestyle="--", alpha=0.5)

        # --- 下段: Type II Error Rate = 1 - Power ---
        ax1 = axes[1]
        if has_type2:
            for method, grp in df_sweep_power.groupby("Method"):
                grp = grp.sort_values("cvr_concentration")
                ax1.plot(
                    grp["cvr_concentration"], grp["type2"],
                    marker="s", label=method, color=colors.get(method, "gray"),
                    linewidth=2, linestyle="--"
                )
                ax1.fill_between(
                    grp["cvr_concentration"],
                    grp["ci_low_type2"], grp["ci_high_type2"],
                    alpha=0.15, color=colors.get(method, "gray")
                )
        ax1.set_ylabel("Type II Error Rate = 1 - Power (with 95% CI)", fontsize=11)
        ax1.set_title(
            "CVR Concentration vs Type II Error Rate\n"
            "(higher = missing real effects; Z-Test may appear artificially powerful)",
            fontsize=11
        )
        ax1.set_ylim(0, 1.05)
        ax1.legend(fontsize=10)
        ax1.grid(True, linestyle="--", alpha=0.5)

        # 共通のX軸設定
        ax1.set_xscale("log")
        ax1.set_xlabel("cvr_concentration (larger = more uniform CVR across users)", fontsize=11)
        xtick_vals = sorted(df_sweep["cvr_concentration"].unique()) if has_type1 else \
                     sorted(df_sweep_power["cvr_concentration"].unique())
        ax1.set_xticks(xtick_vals)
        ax1.set_xticklabels([str(v) for v in xtick_vals])

        plt.suptitle(
            "CVR Concentration Sweep: Type I vs Type II Error Rate\n"
            "Z-Test vs Bootstrap (correlated scenario, repeat_multiplier=1.5)",
            fontsize=13, y=1.01
        )
        plt.tight_layout()
        plt.savefig(os.path.join(args.batch_dir, "cvr_sweep.png"), dpi=150, bbox_inches="tight")
        plt.close()
        print("Created: cvr_sweep.png")
    else:
        print("No CVR sweep data found. Skipping cvr_sweep.png.")

    # -------------------------------------------------------
    # Figure 3: 必要サンプル数の比較（power_calibrated のみ）
    # power_calibrated_{type1_error|power} の sample_sizes.csv を読み込む
    # -------------------------------------------------------
    sample_size_dfs = []
    for pc_dir in ["power_calibrated_type1_error", "power_calibrated_power"]:
        csv_path = os.path.join(args.batch_dir, pc_dir, "sample_sizes.csv")
        if os.path.exists(csv_path):
            df_ss = pd.read_csv(csv_path)
            df_ss["source"] = pc_dir
            sample_size_dfs.append(df_ss)

    if sample_size_dfs:
        df_all_ss = pd.concat(sample_size_dfs, ignore_index=True)

        # long format に変換
        df_long = pd.melt(
            df_all_ss,
            id_vars=["trial", "source"],
            value_vars=["n_users_z", "n_users_bs"],
            var_name="Method",
            value_name="n_users"
        )
        df_long["Method"] = df_long["Method"].map({
            "n_users_z":  "Z-Test\n(sessions independent)",
            "n_users_bs": "Bootstrap\n(user-level variance)",
        })

        fig, ax = plt.subplots(figsize=(8, 6))

        sns.boxplot(
            data=df_long, x="Method", y="n_users", hue="Method",
            palette={"Z-Test\n(sessions independent)": "blue",
                     "Bootstrap\n(user-level variance)":  "orange"},
            width=0.4, linewidth=1.5, ax=ax, legend=False
        )

        # 平均値をテキストで注釈
        for i, method in enumerate(df_long["Method"].unique()):
            mean_val = df_long[df_long["Method"] == method]["n_users"].mean()
            ax.text(
                i, mean_val + df_long["n_users"].max() * 0.02,
                f"Mean = {mean_val:.0f}",
                ha="center", va="bottom", fontsize=10, fontweight="bold",
                color="black"
            )

        ax.set_xlabel("Method", fontsize=12)
        ax.set_ylabel("Required Sample Size (n_users per experiment)", fontsize=11)
        ax.set_title(
            "Required Sample Size Comparison: Z-Test vs Bootstrap\n"
            "(power_calibrated scenario: each box = distribution across trials)",
            fontsize=12
        )
        ax.grid(True, linestyle="--", alpha=0.5, axis="y")

        # 比率の注釈
        mean_z  = df_long[df_long["Method"].str.startswith("Z-Test")]["n_users"].mean()
        mean_bs = df_long[df_long["Method"].str.startswith("Bootstrap")]["n_users"].mean()
        if mean_z > 0:
            ratio = mean_bs / mean_z
            ax.text(
                0.98, 0.05,
                f"Bootstrap / Z-Test = {ratio:.2f}x\n(Bootstrap needs ~{ratio:.1f}x more users)",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=10, color="gray",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", edgecolor="gray")
            )

        plt.tight_layout()
        plt.savefig(os.path.join(args.batch_dir, "sample_size.png"), dpi=150, bbox_inches="tight")
        plt.close()
        print("Created: sample_size.png")
    else:
        print("No sample_sizes.csv found. Skipping sample_size.png.")


if __name__ == "__main__":
    main()
