# %% item_mlp_train_interaction.py
import sqlite3
import pandas as pd
import os, json
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.model_selection import train_test_split
from torch.utils.data import TensorDataset, DataLoader

# ------------------------------
# 경로
# ------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"{BASE_DIR}")
DB_PATH = os.path.join(BASE_DIR, "data", "item_data.db")
JSON_PATH = os.path.join(BASE_DIR, "data", "item.json")
MODEL_PATH = os.path.join(BASE_DIR, "data", "item_model.pth")

# ------------------------------
# MLP 모델 정의
# ------------------------------
class ItemMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, hidden_dim)
        self.bn3 = nn.BatchNorm1d(hidden_dim)
        self.fc4 = nn.Linear(hidden_dim, hidden_dim)
        self.bn4 = nn.BatchNorm1d(hidden_dim)
        self.fc_out = nn.Linear(hidden_dim, output_dim)
        self.dropout = nn.Dropout(0.3)

    def forward(self, x):
        x = F.relu(self.bn1(self.fc1(x)))
        x = self.dropout(x)
        x = F.relu(self.bn2(self.fc2(x)))
        x = self.dropout(x)
        x = F.relu(self.bn3(self.fc3(x)))
        x = self.dropout(x)
        x = F.relu(self.bn4(self.fc4(x)))
        x = self.dropout(x)
        return torch.sigmoid(self.fc_out(x))

# ------------------------------
# 입력 벡터 생성
# ------------------------------
def build_input_vector(my_roles, enemy_roles, num_roles, role2idx):
    my_vec = torch.zeros(num_roles)
    for r in my_roles:
        if r in role2idx:
            my_vec[role2idx[r]] = 1.0

    enemy_vec = torch.zeros(num_roles)
    for roles in enemy_roles:
        for r in roles:
            if r in role2idx:
                enemy_vec[role2idx[r]] += 1.0

    interaction_vec = torch.ger(my_vec, enemy_vec).view(-1)
    return torch.cat([my_vec, enemy_vec, interaction_vec], dim=0)

# ------------------------------
# 라벨 생성
# ------------------------------
def build_labels(item_str, valid_items):
    y = torch.zeros(len(valid_items))
    for i in item_str.split(','):
        i = i.strip()
        if i and int(i) in valid_items:
            y[valid_items.index(int(i))] = 1.0
    return y

# ------------------------------
# 학습 및 모델 저장 함수
# ------------------------------
def train_and_save_item_mlp(DB_PATH, JSON_PATH, MODEL_PATH,
                            hidden_dim=512, batch_size=64, epochs=10, lr=0.01,
                            role_list=None):
    if role_list is None:
        role_list = ['Tank','Fighter','Marksman','Assassin','Mage','Support']

    # DB 로드
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM item_feedback", conn)
    conn.close()

    # JSON 로드
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        item_data = json.load(f)

    # 역할
    role2idx = {r:i for i,r in enumerate(role_list)}
    num_roles = len(role2idx)

    # 유효 아이템
    all_item_ids = set()
    for items_str in df['my_items']:
        for i in items_str.split(','):
            if i.strip():
                all_item_ids.add(int(i.strip()))
    valid_items = sorted([i for i in all_item_ids if item_data['data'].get(str(i), {}).get('gold', {}).get('total',0) >= 2200])
    num_items = len(valid_items)

    # 데이터셋 준비
    X_list, Y_list = [], []
    for _, row in df.iterrows():
        my_roles_row = [r.strip() for r in row['my_role'].split(',') if r.strip()]
        enemy_roles_row = [[er.strip() for er in r.split('|') if er.strip()] for r in row['enemy_roles'].split(';')]
        X_list.append(build_input_vector(my_roles_row, enemy_roles_row, num_roles, role2idx))
        Y_list.append(build_labels(row['my_items'], valid_items))

    X = torch.stack(X_list)
    Y = torch.stack(Y_list)

    train_X, test_X, train_Y, test_Y = train_test_split(X, Y, test_size=0.2, random_state=42)
    train_loader = DataLoader(TensorDataset(train_X, train_Y), batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(TensorDataset(test_X, test_Y), batch_size=batch_size)

    # 모델 학습
    input_dim = num_roles*2 + num_roles*num_roles
    model = ItemMLP(input_dim=input_dim, hidden_dim=hidden_dim, output_dim=num_items)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.BCELoss()

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0
        for bx, by in train_loader:
            optimizer.zero_grad()
            out = model(bx)
            loss = criterion(out, by)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * bx.size(0)
        print(f"Epoch {epoch+1}/{epochs}, Loss: {epoch_loss/len(train_X):.4f}")

    # 테스트
    model.eval()
    test_loss = 0
    with torch.no_grad():
        for bx, by in test_loader:
            out = model(bx)
            test_loss += criterion(out, by).item() * bx.size(0)
    print(f"Test BCE Loss: {test_loss/len(test_X):.4f}")

    # 모델 저장
    torch.save({
        'model_state': model.state_dict(),
        'valid_items': valid_items,
        'role2idx': role2idx,
        'num_roles': num_roles
    }, MODEL_PATH)
    print(f"모델 저장 완료: {MODEL_PATH}")

    return model, valid_items, role2idx, num_roles, item_data

# ------------------------------
# 모델 로드 함수
# ------------------------------
def load_item_model(model_path=MODEL_PATH):
    checkpoint = torch.load(model_path, map_location='cpu')
    role2idx = checkpoint['role2idx']
    num_roles = checkpoint['num_roles']
    valid_items = checkpoint['valid_items']

    input_dim = num_roles*2 + num_roles*num_roles
    model = ItemMLP(input_dim=input_dim, hidden_dim=512, output_dim=len(valid_items))
    model.load_state_dict(checkpoint['model_state'])
    model.eval()

    # item_data도 함께 로드
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "data", "item.json")
    with open(json_path, "r", encoding="utf-8") as f:
        item_data = json.load(f)

    return model, valid_items, role2idx, num_roles, item_data


# ------------------------------
# 추천 함수
# ------------------------------
def recommend_items(my_roles, enemy_roles, top_n=5, model=None, valid_items=None, role2idx=None, num_roles=None, item_data=None):
    vec = build_input_vector(my_roles, enemy_roles, num_roles, role2idx)
    with torch.no_grad():
        scores = model(vec.unsqueeze(0)).squeeze()
        topk_indices = torch.topk(scores, top_n).indices.tolist()
        top_items = [item_data['data'][str(valid_items[i])]['name'] for i in topk_indices]
    return top_items

# ------------------------------
# 실행 예시
# ------------------------------
if __name__ == "__main__":
    #train_and_save_item_mlp(DB_PATH, JSON_PATH, MODEL_PATH)

    item_model, valid_items, role2idx, num_roles, item_data = load_item_model()
    my_roles = ['Marksman']
    enemy_roles = [
        ['Assassin'],
        ['Assassin'],
        ['Assassin'],
        ['Marksman','Mage'],
        ['Mage','Support']
    ]
    top_items = recommend_items(
        my_roles, 
        enemy_roles, 
        top_n=5,
        model=item_model,
        valid_items=valid_items,
        role2idx=role2idx,
        num_roles=num_roles,
        item_data=item_data
    )
    print("추천 아이템:", top_items)

# %%
