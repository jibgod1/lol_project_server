# %%
import sqlite3
import pandas as pd
import numpy as np
import os
import json
from sklearn.preprocessing import MultiLabelBinarizer
from fastfm import sgd
from scipy.sparse import csr_matrix, hstack

# 1️⃣ DB와 JSON 경로
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "item_data.db")
JSON_PATH = os.path.join(BASE_DIR, "data", "item.json")

# 2️⃣ DB 불러오기
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM item_feedback", conn)
conn.close()

# 3️⃣ JSON 읽기 (아이템 정보)
with open(JSON_PATH, "r", encoding="utf-8") as f:
    item_data = json.load(f)

# 2200원 이상 아이템만 사용
valid_items = [int(k) for k, v in item_data["data"].items() if v.get("gold", {}).get("total", 0) >= 2200]

# 4️⃣ 역할과 아이템 파싱
def parse_roles_simple(role_str):
    """각 챔피언의 역할 문자열 그대로 하나로 처리"""
    if role_str and role_str.strip() != "":
        return [role_str.strip()]
    return []

def parse_items(item_str):
    if not item_str or item_str.strip() == "":
        return []
    items = []
    for i in item_str.split(','):
        if i.strip() == "":
            continue
        try:
            item_id = int(i)
            if item_id in valid_items:
                items.append(item_id)
        except ValueError:
            continue
    return items

df['my_roles_list'] = df['my_role'].apply(parse_roles_simple)
df['enemy_roles_list'] = df['enemy_roles'].apply(lambda x: [r.strip() for r in x.split(',') if r.strip() != ""])
df['my_items_list'] = df['my_items'].apply(parse_items)

# 5️⃣ MultiLabelBinarizer로 벡터화
mlb_my_roles = MultiLabelBinarizer()
X_my_roles = mlb_my_roles.fit_transform(df['my_roles_list'])

mlb_enemy_roles = MultiLabelBinarizer()
X_enemy_roles = mlb_enemy_roles.fit_transform(df['enemy_roles_list'])

mlb_items = MultiLabelBinarizer(classes=valid_items)
X_items = mlb_items.fit_transform(df['my_items_list'])

# 6️⃣ 모든 피쳐 합치기
X = hstack([X_my_roles, X_items, X_enemy_roles])
y = df['win'].values

# 7️⃣ FM 모델 학습
fm_model = sgd.FMClassification(n_iter=30, init_stdev=0.1, rank=8, l2_reg_w=0.1, l2_reg_V=0.1, step_size=0.01)
fm_model.fit(X, y)

# 8️⃣ 추천 함수
def recommend_items_fm(my_role_input, enemy_roles_input, top_n=5):
    # 8-1️⃣ 입력 벡터화
    X_my_role_input = mlb_my_roles.transform([[my_role_input]])
    X_enemy_roles_input = mlb_enemy_roles.transform([enemy_roles_input])
    
    scores = []
    for item_id in mlb_items.classes_:
        X_item_input = mlb_items.transform([[item_id]])
        X_input = hstack([X_my_role_input, X_item_input, X_enemy_roles_input])
        score = fm_model.predict(X_input)[0]
        scores.append((item_id, score))
    
    # 8-2️⃣ 상위 top_n 선택
    scores.sort(key=lambda x: x[1], reverse=True)
    top_items = [(item_data["data"][str(item_id)]["name"], score) for item_id, score in scores[:top_n]]
    return top_items

# 9️⃣ 사용 예시
my_role = 'Fighter'  # 내 역할
enemy_roles = ['Assassin', 'Mage', 'Tank', 'Support', 'Marksman']  # 상대 역할
recommended = recommend_items_fm(my_role, enemy_roles, top_n=5)
print("추천 아이템:", recommended)

# %%
