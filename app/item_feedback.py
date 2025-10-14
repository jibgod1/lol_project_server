# %%
import torch
from item_model import ItemRecommender, role2idx, enemy_roles_to_idx, used_item_idx, valid_items, item_data, MODEL_PATH


def recommend_items_filtered(my_roles_input, enemy_roles_input, top_n=5):
    checkpoint = torch.load(MODEL_PATH)
    loaded_model = ItemRecommender(
        num_roles=checkpoint['num_roles'],
        num_enemy_roles=checkpoint['num_enemy_roles'],
        num_items=checkpoint['num_items']
    )
    loaded_model.load_state_dict(checkpoint['model_state'])
    loaded_model.eval()
    
    if isinstance(my_roles_input, str):
        my_roles_input = [my_roles_input]
    my_roles_idx_input = [role2idx[r] for r in my_roles_input if r in role2idx]
    enemy_idx_input = torch.tensor([enemy_roles_to_idx(enemy_roles_input)], dtype=torch.long)
    
    with torch.no_grad():
        pred = loaded_model