import numpy as np
import pandas as pd


def generate_pre_experiment_data(config, n_pre_users):
    """
    事前観測フェーズのデータを生成する（AB分割なし）。

    実際の運用では、AB実験を開始する前に既存のユーザー行動ログを観察して
    ベースラインのCVRを推定する。このフェーズでは全ユーザーを「コントロール群」として
    扱い、相関あり・ユーザーCVR偏りありのデータを生成する。

    Args:
        config (dict): シミュレーション設定
        n_pre_users (int): 事前観測フェーズのユーザー数

    Returns:
        p_a_session (float): セッション独立仮定でのCVR = Σconv / Σsessions
                             Z検定のサンプル数計算で使用する
        p_a_user (float):    ユーザーレベル平均CVR = mean(user_cvr_i)
                             参照用・Bootstrap計算の基準値
        var_user_cvr (float): ユーザーレベルCVRの標本分散（Bessel補正あり）
                              Bootstrap のサンプル数計算で使用する
    """
    base_rate = config["base_rate"]
    sessions_per_user = config["sessions_per_user"]
    cvr_concentration = config.get("cvr_concentration", 100000.0)
    repeat_multiplier = config.get("repeat_multiplier", 1.0)

    # ユーザーCVRのベータ分布パラメータ
    alpha_param = base_rate * cvr_concentration
    beta_param = (1.0 - base_rate) * cvr_concentration

    # 全ユーザーにベースCVRを割り当て（AB分割なし）
    base_cvrs = np.random.beta(alpha_param, beta_param, size=n_pre_users)
    user_ids = [f"PRE{i:06d}" for i in range(1, n_pre_users + 1)]

    # セッションログの生成
    session_records = []
    for uid, base_cvr in zip(user_ids, base_cvrs):
        for s_idx in range(sessions_per_user):
            # 2回目以降のセッションは repeat_multiplier を適用（離脱率の低いリピーターモデル）
            current_cvr = base_cvr if s_idx == 0 else min(base_cvr * repeat_multiplier, 1.0)
            conversion = np.random.binomial(1, current_cvr)
            session_records.append({
                "user_id": uid,
                "session_index": s_idx,
                "group": "A",
                "base_cvr": base_cvr,
                "cvr": current_cvr,
                "conversion": conversion,
            })

    session_logs = pd.DataFrame(session_records)

    # --- Z検定用: セッション独立仮定での CVR ---
    # 「全セッションが独立した試行」として単純な合計で計算する
    p_a_session = session_logs["conversion"].sum() / len(session_logs)

    # --- Bootstrap用: ユーザーレベルの CVR 分散 ---
    # 各ユーザーの平均CVRを計算し、その分布の分散を求める
    user_cvr = session_logs.groupby("user_id")["conversion"].mean()
    p_a_user = float(user_cvr.mean())
    var_user_cvr = float(user_cvr.var())  # Bessel補正あり（ddof=1）

    return p_a_session, p_a_user, var_user_cvr
