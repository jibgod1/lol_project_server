# %%
import sqlite3
import pandas as pd
import numpy as np
import os
import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split

# ------------------------------
# 경로 설정
# ------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "item_data.db")
JSON_PATH = os.path.join(BASE_DIR, "data", "item.json")
MODEL_PATH = os.path.join(BASE_DIR, "data", "item_feedback.pth")

# ------------------------------
# 데이터 불러오기
# ------------------------------
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM item_feedback", conn)
conn.close()

with open(JSON_PATH, "r", encoding="utf-8") as f:
    item_data = json.load(f)

valid_items = [int(k) for k, v in item_data["data"].items() if v.get("gold", {}).get("total", 0) >= 2200]

# ------------------------------
# 파싱 함수
# ------------------------------
def parse_roles(role_str):
    if not role_str or role_str.strip() == "":
        return []
    return [r.strip() for r in role_str.split(',')]

def parse_enemy_roles(enemy_str):
    champions = enemy_str.split(';')
    res = []
    for champ in champions:
        roles = [r.strip() for r in champ.split('|') if r.strip() != '']
        res.append(roles)
    return res

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

# ------------------------------
# 데이터 전처리
# ------------------------------
df['my_roles_list'] = df['my_role'].apply(parse_roles)
df['enemy_roles_list'] = df['enemy_roles'].apply(parse_enemy_roles)
df['my_items_list'] = df['my_items'].apply(parse_items)

# 내 역할 인덱스
all_my_roles = list(set([r for sublist in df['my_roles_list'] for r in sublist]))
role2idx = {r:i for i,r in enumerate(all_my_roles)}
df['my_roles_idx'] = df['my_roles_list'].apply(lambda lst: [role2idx[r] for r in lst if r in role2idx])

# 상대 역할 인덱스
all_enemy_roles = list(set([role for champ in df['enemy_roles_list'] for role in champ if isinstance(role, str)]))
role2idx_enemy = {r:i for i,r in enumerate(all_enemy_roles)}
num_enemy_roles = len(role2idx_enemy)
max_enemy = 5

def enemy_roles_to_idx(champ_roles_list):
    idx_list = []
    for champ_roles in champ_roles_list:
        idxs = [role2idx_enemy[r] for r in champ_roles if r in role2idx_enemy]
        if len(idxs) > 0:
            idx_list.append(np.mean(idxs))
        else:
            idx_list.append(num_enemy_roles)  # padding
    while len(idx_list) < max_enemy:
        idx_list.append(num_enemy_roles)
    return idx_list[:max_enemy]

df['enemy_roles_idx'] = df['enemy_roles_list'].apply(enemy_roles_to_idx)

# 아이템 인덱스
item2idx = {item_id:i for i,item_id in enumerate(valid_items)}
df['my_items_idx'] = df['my_items_list'].apply(lambda lst: [item2idx[i] for i in lst if i in item2idx])

used_item_idx = set([i for sublist in df['my_items_idx'] for i in sublist])

# ------------------------------
# Dataset
# ------------------------------
win_factor = 0.3  # 승리 가중치

class ItemDataset(Dataset):
    def __init__(self, df, max_enemy=5):
        self.my_roles_list = df['my_roles_idx'].tolist()
        self.enemy_roles = torch.tensor(df['enemy_roles_idx'].tolist(), dtype=torch.long)
        y = np.zeros((len(df), len(valid_items)), dtype=np.float32)
        for i, row in enumerate(df['my_items_idx']):
            if not row:
                continue
            for idx in row:
                if idx >= y.shape[1]:
                    continue
                if df.iloc[i]['win'] == 1:
                    y[i, idx] = 1.0 + win_factor
                else:
                    y[i, idx] = 1.0 - win_factor
        y = np.clip(y, 0.0, 1.0)
        self.y = torch.tensor(y, dtype=torch.float32)
        self.max_enemy = max_enemy
    
    def __len__(self):
        return len(self.y)
    
    def __getitem__(self, idx):
        return self.my_roles_list[idx], self.enemy_roles[idx], self.y[idx]

# ------------------------------
# 학습/테스트 분리
# ------------------------------
dataset = ItemDataset(df)
train_size = int(0.8 * len(dataset))
test_size = len(dataset) - train_size
train_dataset, test_dataset = random_split(dataset, [train_size, test_size])

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, collate_fn=lambda batch: batch)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False, collate_fn=lambda batch: batch)

# ------------------------------
# 모델 정의
# ------------------------------
class ItemRecommender(nn.Module):
    def __init__(self, num_roles, num_enemy_roles, num_items, embed_dim=16, hidden_dim=128, max_enemy=5):
        super(ItemRecommender, self).__init__()
        self.role_embed = nn.Embedding(num_roles, embed_dim)
        self.enemy_embed = nn.Embedding(num_enemy_roles+1, embed_dim, padding_idx=num_enemy_roles)
        self.fc1 = nn.Linear(embed_dim*2, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc_out = nn.Linear(hidden_dim, num_items)
        self.sigmoid = nn.Sigmoid()
        self.max_enemy = max_enemy
    
    def forward(self, my_roles_idx_list, enemy_idx):
        role_vecs = []
        for role_idxs in my_roles_idx_list:
            role_tensor = torch.tensor(role_idxs, dtype=torch.long)
            role_emb = self.role_embed(role_tensor)
            role_vecs.append(role_emb.mean(dim=0))
        role_vec = torch.stack(role_vecs)
        enemy_vec = self.enemy_embed(enemy_idx).mean(dim=1)
        x = torch.cat([role_vec, enemy_vec], dim=1)
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = self.sigmoid(self.fc_out(x))
        return x

model = ItemRecommender(num_roles=len(role2idx), num_enemy_roles=num_enemy_roles, num_items=len(valid_items))

# ------------------------------
# 학습
# ------------------------------
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
criterion = nn.BCELoss()

for batch in train_loader:
    optimizer.zero_grad()
    my_roles_batch, enemy_batch, y_batch = zip(*batch)
    outputs = model(list(my_roles_batch), torch.stack(enemy_batch))
    y_batch_tensor = torch.stack(y_batch)
    loss = criterion(outputs, y_batch_tensor)
    loss.backward()
    optimizer.step()

# ------------------------------
# 테스트 평가
# ------------------------------
model.eval()
total_loss = 0
with torch.no_grad():
    for batch in test_loader:
        my_roles_batch, enemy_batch, y_batch = zip(*batch)
        outputs = model(list(my_roles_batch), torch.stack(enemy_batch))
        y_batch_tensor = torch.stack(y_batch)
        loss = criterion(outputs, y_batch_tensor)
        total_loss += loss.item()
print(f"테스트 BCE Loss: {total_loss/len(test_loader):.4f}")

# ------------------------------
# 모델 저장
# ------------------------------
checkpoint = {
    'model_state': model.state_dict(),
    'num_roles': len(role2idx),
    'num_enemy_roles': num_enemy_roles,
    'num_items': len(valid_items)
}
torch.save(checkpoint, MODEL_PATH)
print(f"모델 저장 완료: {MODEL_PATH}")

# %%
