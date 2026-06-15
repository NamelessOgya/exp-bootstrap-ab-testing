import numpy as np

def run_bootstrap_test(session_logs_df, bootstrap_iter=1000, return_dist=False, one_sided=False):
    """
    ユーザー（クラスター）単位でリサンプリングを行い、Bootstrap検定を実行する。
    - 同一ユーザー内のセッション間相関を維持するため、ユーザー単位で重複を許してリサンプリング（クラスターブートストラップ）。
    - 処理高速化のため、あらかじめユーザーごとのCV数とセッション数を集計してサンプリングします。
    - one_sided=True の場合、B > A の片側p値を返す。
    """
    df_a = session_logs_df[session_logs_df["group"] == "A"]
    df_b = session_logs_df[session_logs_df["group"] == "B"]
    
    n_obs_a = len(df_a)
    n_obs_b = len(df_b)
    
    if n_obs_a == 0 or n_obs_b == 0:
        if return_dist:
            return 1.0, np.zeros(bootstrap_iter), 0.0, 0.0
        return 1.0
        
    cvr_a_obs = df_a["conversion"].sum() / n_obs_a
    cvr_b_obs = df_b["conversion"].sum() / n_obs_b
    theta_obs = cvr_b_obs - cvr_a_obs
    
    # ユーザーIDのリストを取得
    users_a = df_a["user_id"].unique()
    users_b = df_b["user_id"].unique()
    
    n_users_a = len(users_a)
    n_users_b = len(users_b)
    
    if n_users_a == 0 or n_users_b == 0:
        if return_dist:
            return 1.0, np.zeros(bootstrap_iter), 0.0, 0.0
        return 1.0
        
    # ユーザーごとのコンバージョン数とセッション数を集計して辞書化（ループ内処理の超高速化のため）
    user_stats = session_logs_df.groupby("user_id")["conversion"].agg(["sum", "count"]).to_dict("index")
    
    # numpy配列化してサンプリング速度を向上
    users_a_arr = np.array(users_a)
    users_b_arr = np.array(users_b)
    
    theta_stars = []
    
    # ブートストラップサンプルの生成
    for _ in range(bootstrap_iter):
        # ユーザー単位での重複を許したサンプリング
        sampled_users_a = np.random.choice(users_a_arr, size=n_users_a, replace=True)
        sampled_users_b = np.random.choice(users_b_arr, size=n_users_b, replace=True)
        
        # サンプルデータの集計
        sum_a = 0
        count_a = 0
        for u in sampled_users_a:
            stat = user_stats[u]
            sum_a += stat["sum"]
            count_a += stat["count"]
            
        sum_b = 0
        count_b = 0
        for u in sampled_users_b:
            stat = user_stats[u]
            sum_b += stat["sum"]
            count_b += stat["count"]
            
        # 比率の差の算出
        p_a_star = sum_a / count_a if count_a > 0 else 0.0
        p_b_star = sum_b / count_b if count_b > 0 else 0.0
        
        theta_stars.append(p_b_star - p_a_star)
        
    theta_stars = np.array(theta_stars)
    
    # 帰無仮説（差が0）の分布を作成するため、実測値を引いて中心化する
    h0_distribution = theta_stars - theta_obs
    
    # p値の計算（両側 or 片側）
    if one_sided:
        # 片側検定（B > A 方向）: H0中心化分布において theta_obs 以上の値が出る確率
        p_value = np.mean(h0_distribution >= theta_obs)
    else:
        # 両側検定
        p_value = np.mean(np.abs(h0_distribution) >= np.abs(theta_obs))
    
    if return_dist:
        # Z検定が独立を仮定して算出する理論上の標準誤差（se_theory）を計算
        count_a = df_a["conversion"].sum()
        count_b = df_b["conversion"].sum()
        p_pool = (count_a + count_b) / (n_obs_a + n_obs_b)
        se_theory = np.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n_obs_a + 1.0 / n_obs_b))
        return p_value, theta_stars, theta_obs, se_theory
        
    return p_value
