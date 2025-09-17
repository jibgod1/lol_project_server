# %%
import sqlite3
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)



# 1. 데이터 불러오기
tier = "GOLD"
lanes = ["TOP","JUNGLE","MIDDLE","BOTTOM","UTILITY"]

for lane in lanes:
    db_path = os.path.join(DATA_DIR, "match_data.db")
    conn1 = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"SELECT * FROM match_id_{tier} WHERE teamposition = '{lane}'", conn1)
    conn1.close()
    
    winrate_path = os.path.join(DATA_DIR, "champion_winrate_data.db")
    conn2 = sqlite3.connect(winrate_path)
    winrate_df = pd.read_sql_query(
        f"SELECT * FROM matchup_data WHERE tier = '{tier.lower()}' AND position = '{lane.lower()}'", conn2
    )
    conn2.close()
    
    winrate_df["hero_name"] = winrate_df["hero_name"].str.lower()
    winrate_df["counter_name"] = winrate_df["counter_name"].str.lower()
    
    winrate_df = winrate_df.rename(columns={"hero_name": "my_champion", "counter_name": "enemy_champion"})
    
    df["my_champion"] = df["my_champion"].str.lower()
    df["enemy_champion"] = df["enemy_champion"].str.lower()
    
    
    df = df.merge(
        winrate_df[["my_champion", "enemy_champion", "win_rate"]],
        on=["my_champion", "enemy_champion"],
        how="left"
    )
    df["win_rate"] = df["win_rate"].fillna(50)
    
     
    # 2. 데이터 분류
    #df.drop(columns=["dragon_participation", "dragon_deaths"], inplace=True)
    #df.drop(columns=["elder_dragon_participation", "elder_dragon_deaths"], inplace=True)
    #df.drop(columns=["baron_nashor_participation", "baron_nashor_deaths"], inplace=True)
    #df.drop(columns=["horde_participation", "horde_deaths"], inplace=True)
    #df.drop(columns=["riftherald_participation", "riftherald_deaths"], inplace=True)
    df.drop(columns=["team_Dragon_kills", "team_Horde_kills", "team_riftHerald_kills", "team_Baron_kills", "team_ElderDragon_kills", "team_Atakhan_kills"], inplace=True)
    df.drop(columns=["kills", "deaths", "assists"], inplace=True)
    df.drop(columns=["early_kills", "early_deaths", "early_assists", "lane_cs"], inplace=True)
    df.drop(columns=["kill_participation"], inplace=True)
    df.drop(columns=["turret_damage"], inplace=True)
    
    # 3. 특성(X)와 타겟(y) 분리
    X = df.drop(columns=["win", "match_id", "teamposition", "my_champion", "enemy_champion"])
    y = df["win"]
    
    # 4. train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    # 5. 스케일링
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 6. 모델 학습
    model = LogisticRegression(max_iter=100)
    model.fit(X_train_scaled, y_train)
    
    # 7. 평가
    y_pred = model.predict(X_test_scaled)
    print(f"[{lane}] 라인 기준 정확도: {accuracy_score(y_test, y_pred):.4f}")
    
    # 8. 특성 중요도 확인
    importance = model.coef_[0]
    for name, val in zip(X.columns, importance):
        print(f"{name:<25}: {val:.4f}")
    
    # 9. 저장
    joblib.dump(model, os.path.join(DATA_DIR, f"model_{lane.lower()}_{tier}.pkl"))
    joblib.dump(scaler, os.path.join(DATA_DIR, f"scaler_{lane.lower()}_{tier}.pkl"))


# %%



