from statsmodels.stats.proportion import proportions_ztest

def run_z_test(session_logs_df, one_sided=False):
    """
    セッションログデータに対して通常の母比率の差の検定（z検定）を実行する。
    - クラスター構造（ユーザー内の相関）を無視し、全セッションを独立した試行と仮定して検定する。
    - one_sided=True の場合、B > A の片側検定を行う（alternative='larger'）。
    """
    df_a = session_logs_df[session_logs_df["group"] == "A"]
    df_b = session_logs_df[session_logs_df["group"] == "B"]
    
    count_a = df_a["conversion"].sum()
    n_obs_a = len(df_a)
    
    count_b = df_b["conversion"].sum()
    n_obs_b = len(df_b)
    
    # どちらかのサンプルサイズが0の場合は検定不可能
    if n_obs_a == 0 or n_obs_b == 0:
        return 1.0, 0.0, 0.0
        
    counts = [count_b, count_a]
    nobs = [n_obs_b, n_obs_a]
    
    # statsmodelsによるz検定 (両側検定)
    # 値が極端に小さい場合などにnanになるのを防ぐため、カウントが全て0の場合は検定をスキップ
    if sum(counts) == 0:
        return 1.0, 0.0, 0.0
        
    # 検定の方向を設定（片側: B > A、両側: デフォルト）
    alternative = 'larger' if one_sided else 'two-sided'

    try:
        stat, p_value = proportions_ztest(counts, nobs, alternative=alternative)
    except Exception:
        p_value = 1.0
        
    cvr_a = count_a / n_obs_a if n_obs_a > 0 else 0.0
    cvr_b = count_b / n_obs_b if n_obs_b > 0 else 0.0
    
    return p_value, cvr_a, cvr_b
