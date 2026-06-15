import pandas as pd
import numpy as np

def generate_imbalanced_data(config):
    """
    ユーザー数の割り付け比率に差があるシナリオのデータ生成を行う。
    - split_ratio（B群の比率）に従ってユーザーを分割。
    - ユーザー間の偏り（cvr_concentration）やリピート効果（repeat_multiplier）も設定から反映する。
    """
    n_users = config["n_users"]
    sessions_per_user = config["sessions_per_user"]
    base_rate = config["base_rate"]
    cvr_concentration = config["cvr_concentration"]
    repeat_multiplier = config["repeat_multiplier"]
    relative_uplift = config["relative_uplift"]
    split_ratio = config["split_ratio"]  # imbalancedシナリオで重視されるパラメータ
    
    # 1. ユーザープロファイルの作成
    user_ids = [f"U{i:06d}" for i in range(1, n_users + 1)]
    
    # グループ分割 (split_ratioを使用)
    groups = np.random.choice(["A", "B"], size=n_users, p=[1 - split_ratio, split_ratio])
    
    # ベータ分布パラメータの計算
    alpha = base_rate * cvr_concentration
    beta_param = (1 - base_rate) * cvr_concentration
    
    # ユーザー固有のベースCVRを生成
    base_cvrs = np.random.beta(alpha, beta_param, size=n_users)
    
    user_profiles = pd.DataFrame({
        "user_id": user_ids,
        "group": groups,
        "base_cvr": base_cvrs
    })
    
    # 2. セッションログデータの作成
    session_records = []
    
    for idx, row in user_profiles.iterrows():
        u_id = row["user_id"]
        group = row["group"]
        b_cvr = row["base_cvr"]
        
        user_initial_cvr = b_cvr
        if group == "B":
            user_initial_cvr = min(b_cvr * (1.0 + relative_uplift), 1.0)
            
        for s_idx in range(sessions_per_user):
            if s_idx == 0:
                current_cvr = user_initial_cvr
            else:
                current_cvr = min(user_initial_cvr * repeat_multiplier, 1.0)
                
            conversion = np.random.binomial(1, current_cvr)
            
            session_records.append({
                "user_id": u_id,
                "session_index": s_idx,
                "group": group,
                "cvr": current_cvr,
                "conversion": conversion
            })
            
    session_logs = pd.DataFrame(session_records)
    
    return user_profiles, session_logs
