# %%
import torch
import numpy as np
from item_model import ItemRecommender, MODEL_PATH


def enemy_roles_to_idx(champ_roles_list, role2idx_enemy, num_enemy_roles):
    idx_list = []
    print("bbb")
    for champ_roles in champ_roles_list:
        idxs = [role2idx_enemy[r] for r in champ_roles if r in role2idx_enemy]
        if len(idxs) > 0:
            idx_list.append(np.mean(idxs))
        else:
            idx_list.append(num_enemy_roles)
    while len(idx_list) < 5:
        idx_list.append(num_enemy_roles)
    return idx_list[:5]


def recommend_items_filtered(my_roles_input, enemy_roles_input, top_n=5):
    checkpoint = torch.load(MODEL_PATH, map_location="cpu")
    print("aaa")
    # checkpoint에서 모든 매핑 데이터 로드
    role2idx = checkpoint["role2idx"]
    role2idx_enemy = checkpoint["role2idx_enemy"]
    valid_items = checkpoint["valid_items"]

    loaded_model = ItemRecommender(
        num_roles=checkpoint["num_roles"],
        num_enemy_roles=checkpoint["num_enemy_roles"],
        num_items=checkpoint["num_items"]
    )
    loaded_model.load_state_dict(checkpoint["model_state"])
    loaded_model.eval()

    # 입력 전처리
    if isinstance(my_roles_input, str):
        my_roles_input = [my_roles_input]
    my_roles_idx_input = [role2idx[r] for r in my_roles_input if r in role2idx]
    enemy_idx_input = torch.tensor(
        [enemy_roles_to_idx(enemy_roles_input, role2idx_enemy, checkpoint["num_enemy_roles"])],
        dtype=torch.long
    )

    # 예측
    with torch.no_grad():
        pred = loaded_model([my_roles_idx_input], enemy_idx_input)
        top_indices = torch.topk(pred, top_n, dim=1).indices[0].tolist()

    top_items = [valid_items[i] for i in top_indices if i < len(valid_items)]
    return top_items