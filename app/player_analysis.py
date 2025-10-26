# %%
from typing import List
import requests
import time
import joblib
import numpy as np
import config
import get_match_id
import game_info
import get_player_puuid
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def ingame_players_id(puuid):
    api_key = config.API_KEY
    ranked_queue_ids = [420]
    region = 'asia'
    headers = {"X-Riot-Token": api_key}
    url = f"https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
    res = requests.get(url, headers=headers)
    while True:
        if res.status_code == 200:
            spec_data = res.json()
            break
        elif res.status_code == 429:
            print("Rate limit... retrying in 10 seconds...")
            time.sleep(10)
        else:
            print(f"[ERROR]  puuid {puuid}: {res.status_code}")
            return

    if spec_data.get("gameMode") != "CLASSIC" or spec_data.get("gameQueueConfigId") not in ranked_queue_ids:
        print("wrong game mode")
        return

    if spec_data != None:
        player_ids = [{"riotId": p["riotId"], "puuid": p["puuid"]} for p in spec_data["participants"]]
        return player_ids




def get_lane(position):
    x = position.get("x", 0)
    y = position.get("y", 0)

    if (5000 <= y <= 16000 and 0 <= x <= 4000) or (0 <= x <= 11000 and 12000 <= y <= 16000):
        return "TOP"
    elif abs(x - y) <= 3000:
        return "MID"
    elif (5000 <= x <= 16000 and 0 <= y <= 4000) or (0 <= y <= 11000 and 12000 <= x <= 16000):
        return "BOT"
    else:
        return "OTHER"  # 정글, 베이스, 강가 등


def generate_feedback(positive, negative, below_avg):
    feedback = {
        "positive": [],
        "negative": [],
        "below_avg": []
    }

    # feature: {coef>0일 때 문구, coef<=0일 때 문구} 딕셔너리
    positive_feedback_dict = {
        "diff_early_k": [
            "라인전에서 킬 우위를 점할때가 많습니다. 공격적으로 상대를 압박해봅시다.",
            "킬 양보를 통해 승리를 도모했습니다. 혼자 움직이는것보다는 팀원과 함께 움직여 팀원을 성장시킵시다."
        ],
        "diff_early_d": [
            "죽음으로 인해 이득을 보는 경우도 있습니다. 상대를 죽일수 있다면 내가 죽더라도 공격적으로 플레이 해 봅시다.",
            "라인전에서의 데스가 낮습니다. 안정적인 플레이로 상대방의 성장을 억제해봅시다."
        ],
        "diff_early_a": [
            "초반 교전 참여도가 높습니다. 초반 교전에 계속 적극적으로 참여하여 상대 라이너와의 차이를 벌려봅시다.",
            "초반 교전을 피하며 상대의 성장을 억제했습니다. 무리한 교전으로 킬을 주지 않도록 합시다."
        ],
        "diff_lane_cs": [
            "견제를 통해 cs차이로 성장차이를 효과적으로 벌렸습니다. 공격적인 플레이로 상대의 성장을 억제합시다.",
            "팀원에게 cs를 양보하여 팀원의 성장을 도왔습니다. 팀원이 cs를 편하게 먹을수 있도록 견제에 신경써봅시다."
        ],
        "late_kills": [
            "중후반 교전에서 킬을 통해 효과적으로 성장했습니다. 적극적인 교전 유도를 통해 차이를 더 벌려봅시다.",
            "중후반 교전에서 킬 양보를 통해 팀원 성장에 기여했습니다. 교전 중 킬을 양보할 수 있다면 양보하도록 합시다."
        ],
        "late_deaths": [
            "중후반 교전에서 팀원 대신 희생하여 팀을 승리로 이끌었습니다.",
            "중후반 교전에서 잘 생존하여 팀을 승리로 이끌었습니다. 어그로 핑퐁을 통해 교전에서 승리하도록 합시다."
        ],
        "late_assists": [
            "중후반 교전에서 어시스트를 통해 팀원의 성장을 도왔습니다. 적극적인 교전 유도를 통해 차이를 더 벌려봅시다.",
            "중후반 교전보다는 운영을 통해 승리를 쟁취했습니다. 꼭 싸움만이 정답인것은 아닙니다. 교전보다는 승리에 집중하도록 합시다."
        ],
        "solo_kills": [
            "1대1 상황에서 상대를 제압했습니다. 사이드 운영에서 상대방을 강하게 압박하도록 합시다.",
            "1대1 상황을 피하며 운영했습니다. 사이드 운영보다는 한타에 참여하며 이득을 보도록 합시다."
        ],
        "enemyjungleminionkills": [
            "상대 정글을 빼먹으며 효과적으로 성장했습니다. 상대 정글 시야 확보를 통해 적극적으로 카정을 들어가도록 합시다.",
            "상대 정글에 들어가지 않으며 안정적으로 플레이했습니다. 갱킹을 통해 성장하도록 합시다."
        ],
        "vision_score": [
            "상대의 위치를 잘 파악할 수 있도록 와드를 설치했습니다. 상대가 자주 이동하는 길목을 파악하고, 그 주변 시야를 장악하도록 합시다.",
            "와드구매보다는 성장에 집중했습니다. 성장을 통해 라인 주도권을 잡는것이 중요합니다."
        ],
        "wards_placed": [
            "와드를 적절히 사용하였습니다. 라인전에서 갱킹 회피를 위해, 혹은 오브젝트 타이밍에 시야 확보를 위해 와드를 사용하도록 합시다.",
            "시야 확보를 위한 무리한 와딩을 지양했습니다. 시야를 확보할때는 팀원과 함께 행동하도록 합시다."
        ],
        "dragon_participation": [
            "드래곤 오브젝트에 적극적으로 참여했습니다. 드래곤 오브젝트 교전에 적극 참여하여 이득을 취하도록 합시다.",
            "드래곤 오브젝트에 집착하지 않고 다른곳에서 이득을 취했습니다. 드래곤에 집착하다 더 큰 손해를 보게될 수도 있습니다."
        ],
        "dragon_deaths": [
            "드래곤 오브젝트 타이밍에 어그로를 끌며 팀원이 이득을 볼 수 있도록 도와주었습니다. 내가 죽고 오브젝트를 챙길수 있다면 적극적으로 싸워봅시다.",
            "드래곤 오브젝트 타이밍에 죽지 않고 안정적이 플레이를 보여주었습니다. 교전에서 자신감을 가지고 싸워봅시다."
        ],
        "elder_dragon_participation": [
            "장로 드래곤 오브젝트에 적극적으로 참여했습니다. 장로 드래곤 오브젝트 교전에 적극 참여하여 이득을 취하도록 합시다.",
            "장로 드래곤 오브젝트에 집착하지 않고 다른곳에서 이득을 취했습니다. 장로 드래곤에 집착하다 더 큰 손해를 보게될 수도 있습니다."
        ],
        "elder_dragon_deaths": [
            "장로 드래곤 오브젝트 타이밍에 어그로를 끌며 팀원이 이득을 볼 수 있도록 도와주었습니다. 내가 죽고 오브젝트를 챙길수 있다면 적극적으로 싸워봅시다.",
            "장로 드래곤 오브젝트 타이밍에 죽지 않고 안정적이 플레이를 보여주었습니다. 교전에서 자신감을 가지고 싸워봅시다."
        ],
        "baron_nashor_participation": [
            "바론 오브젝트에 적극적으로 참여했습니다. 바론 오브젝트 교전에 적극 참여하여 이득을 취하도록 합시다.",
            "바론 오브젝트에 집착하지 않고 다른곳에서 이득을 취했습니다. 바론에 집착하다 더 큰 손해를 보게될 수도 있습니다."
        ],
        "baron_nashor_deaths": [
            "바론 오브젝트 타이밍에 어그로를 끌며 팀원이 이득을 볼 수 있도록 도와주었습니다. 내가 죽고 오브젝트를 챙길수 있다면 적극적으로 싸워봅시다.",
            "바론 오브젝트 타이밍에 죽지 않고 안정적이 플레이를 보여주었습니다. 교전에서 자신감을 가지고 싸워봅시다."
        ],
        "riftherald_participation": [
            "전령 오브젝트에 적극적으로 참여했습니다. 전령 오브젝트 교전에 적극 참여하여 이득을 취하도록 합시다.",
            "전령 오브젝트에 집착하지 않고 다른곳에서 이득을 취했습니다. 전령에 집착하다 더 큰 손해를 보게될 수도 있습니다."
        ],
        "riftherald_deaths": [
            "전령 오브젝트 타이밍에 어그로를 끌며 팀원이 이득을 볼 수 있도록 도와주었습니다. 내가 죽고 오브젝트를 챙길수 있다면 적극적으로 싸워봅시다.",
            "전령 오브젝트 타이밍에 죽지 않고 안정적이 플레이를 보여주었습니다. 교전에서 자신감을 가지고 싸워봅시다."
        ],
        "horde_participation": [
            "유충 오브젝트에 적극적으로 참여했습니다. 유충 오브젝트 교전에 적극 참여하여 이득을 취하도록 합시다.",
            "유충 오브젝트에 집착하지 않고 다른곳에서 이득을 취했습니다. 유충에 집착하다 더 큰 손해를 보게될 수도 있습니다."
        ],
        "horde_deaths": [
            "유충 오브젝트 타이밍에 어그로를 끌며 팀원이 이득을 볼 수 있도록 도와주었습니다. 내가 죽고 오브젝트를 챙길수 있다면 적극적으로 싸워봅시다.",
            "유충 오브젝트 타이밍에 죽지 않고 안정적이 플레이를 보여주었습니다. 교전에서 자신감을 가지고 싸워봅시다."
        ],
        "atakhan_participation": [
            "아타칸 오브젝트에 적극적으로 참여했습니다. 아타칸 오브젝트 교전에 적극 참여하여 이득을 취하도록 합시다.",
            "아타칸 오브젝트에 집착하지 않고 다른곳에서 이득을 취했습니다. 아타칸에 집착하다 더 큰 손해를 보게될 수도 있습니다."
        ],
        "atakhan_deaths": [
            "아타칸 오브젝트 타이밍에 어그로를 끌며 팀원이 이득을 볼 수 있도록 도와주었습니다. 내가 죽고 오브젝트를 챙길수 있다면 적극적으로 싸워봅시다.",
            "아타칸 오브젝트 타이밍에 죽지 않고 안정적이 플레이를 보여주었습니다. 교전에서 자신감을 가지고 싸워봅시다."
        ]
    }

    negative_feedback_dict = {
        "diff_early_k": [
            "라인전에서 킬을 많이 못먹어 불리한 상황이 많습니다.",
            "가능하다면 라인전에서 킬을 먹기보다는 양보해주는게 좋습니다."
        ],
        "diff_early_d": [
            "팀원을 위해 희생하는게 좋을때도 있습니다. 나의 죽음으로 팀원들을 살릴수 있다면 여러명을 살리는 방향을 택하도록 합시다.",
            "라인전 데스가 높은편입니다. 킬각을 인지하고 위험할때는 귀한을 하도록 합시다."
        ],
        "diff_early_a": [
            "초반 교전 참여율이 낮습니다. 로밍이나 정글을 적극적으로 도와봅시다.",
            "킬 양보가 과도하여 본인 성장이 늦어졌습니다."
        ],
        "diff_lane_cs": [
            "라인전 cs차이가 많이납니다. 불리하더라고 라인관리를 통해 최대한 cs를 챙기도록 합시다.",
            "라인전 cs가 너무 높습니다. cs 양보를 통해 팀원 성장을 도와주도록 합시다."
        ],
        "late_kills": [
            "중후반 킬이 낮습니다. 적절한 교전 참여와 킬 캐치로 성장을 하도록 합시다.",
            "중후반 킬이 높습니다. 킬 양보를 통해 다른 팀원의 성장을 돕도록 합시다."
        ],
        "late_deaths": [
            "중후반 데스가 적습니다. 팀원을 살릴수 있다면 적극적으로 싸워 팀원들 살리고 대신 죽도록 합시다.",
            "중후반 데스가 많습니다. 맵리딩을 통해 상대 위치를 예측하고 위험한 곳은 팀원과 같이 행동하도록 합시다."
        ],
        "late_assists": [
            "중후반 어시스트가 적습니다. 교전 참여를 통해 어시스트를 올리고 싸움에서 승리할 수 있도록 합시다.",
            "중후반 어시스트가 많습니다. 교전 참여보다는 운영을 통해 게임을 풀어갈 수 있도록 합시다."
        ],
        "solo_kills": [
            "솔로킬이 적습니다. 1대1 상황에서 이길수 있을거같다면 적극적으로 싸워보도록 합시다.",
            "1대1 상황이 많습니다. 팀원들과 같이 행동하고 가능하면 킬을 양보하도록 합시다."
        ],
        "enemyjungleminionkills": [
            "상대 정글몹을 거의 신경쓰지 않고있습니다. 가능하다면 상대 정글을 빼먹으며 성장하도록 합시다.",
            "상대 정글몹에 너무 신경을 많이쓰고 있습니다. 상대 정글을 들어가기 보다는 우리 정글에서 안정적으로 플레이 하도록 합시다."
        ],
        "vision_score": [
            "시야 점수가 낮습니다. 적절한 위치에 와딩을 통해 상대방 위치를 파악하도록 합시다.",
            "시야 점수가 높습니다. 와딩을 위해 너무 많은 골드를 소모하지 않도록 합시다."
        ],
        "wards_placed": [
            "와드를 많이 사용하지 않습니다. 장신구 와들 배치를 소홀히 하지 않도록 합시다.",
            "너무 많은 와드를 사용하고 있습니다. 와드를 남용하지 말고 와드를 구매하는데 너무 많은 골드를 소모하지 않도록 합시다."
        ],
        "dragon_participation": [
            "드래곤 오브젝트 참여율이 낮습니다. 가능하다면 드래곤 오브젝트 싸움에 참가하도록 합시다.",
            "드래곤 오브젝트 참여율이 높습니다. 무리하게 드래곤 오브젝트 싸움에 참여하지 않아도 되니 다른곳에서 이득을 챙기도록 합시다."
        ],
        "dragon_deaths": [
            "드래곤 오브젝트 타이밍에 너무 안정적으로 플레이합니다. 죽더라도 오브젝트를 챙기면 이득이기에 과감하게 플레이해도록 합시다.",
            "드래곤 오브젝트 타이밍에 죽는 경우가 많습니다. 드래곤 오브젝트 타이밍에 안정적으로 플레이하도록 합시다."
        ],
        "elder_dragon_participation": [
            "장로 드래곤 오브젝트 참여율이 낮습니다. 가능하다면 장로 드래곤 오브젝트 싸움에 참가하도록 합시다.",
            "장로 드래곤 오브젝트 참여율이 높습니다. 무리하게 장로 드래곤 오브젝트 싸움에 참여하지 않아도 되니 다른곳에서 이득을 챙기도록 합시다."
        ],
        "elder_dragon_deaths": [
            "장로 드래곤 오브젝트 타이밍에 너무 안정적으로 플레이합니다. 죽더라도 오브젝트를 챙기면 이득이기에 과감하게 플레이해도록 합시다.",
            "장로 드래곤 오브젝트 타이밍에 죽는 경우가 많습니다. 드래곤 오브젝트 타이밍에 안정적으로 플레이하도록 합시다."
        ],
        "baron_nashor_participation": [
            "바론 오브젝트 참여율이 낮습니다. 가능하다면 바론 오브젝트 싸움에 참가하도록 합시다.",
            "바론 오브젝트 참여율이 높습니다. 무리하게 바론 오브젝트 싸움에 참여하지 않아도 되니 다른곳에서 이득을 챙기도록 합시다."
        ],
        "baron_nashor_deaths": [
            "바론 오브젝트 타이밍에 너무 안정적으로 플레이합니다. 죽더라도 오브젝트를 챙기면 이득이기에 과감하게 플레이해도록 합시다.",
            "바론 오브젝트 타이밍에 죽는 경우가 많습니다. 사이드 운영이나 시야 체크를 안정적으로 하도록 합시다."
        ],
        "riftherald_participation": [
            "전령 오브젝트 참여율이 낮습니다. 가능하다면 전령 오브젝트 싸움에 참가하도록 합시다.",
            "전령 오브젝트 참여율이 높습니다. 무리하게 전령 오브젝트 싸움에 참여하지 않아도 되니 다른곳에서 이득을 챙기도록 합시다."
        ],
        "riftherald_deaths": [
            "전령 오브젝트 타이밍에 너무 안정적으로 플레이합니다. 죽더라도 오브젝트를 챙기면 이득이기에 과감하게 플레이해도록 합시다.",
            "전령 오브젝트 타이밍에 죽는 경우가 많습니다. 전령 오브젝트 타이밍에 안정적으로 플레이하도록 합시다."
        ],
        "horde_participation": [
            "유충 오브젝트 참여율이 낮습니다. 가능하다면 드래곤 오브젝트 싸움에 참가하도록 합시다.",
            "유충 오브젝트 참여율이 높습니다. 무리하게 유충 오브젝트 싸움에 참여하지 않아도 되니 다른곳에서 이득을 챙기도록 합시다."
        ],
        "horde_deaths": [
            "유충 오브젝트 타이밍에 너무 안정적으로 플레이합니다. 죽더라도 오브젝트를 챙기면 이득이기에 과감하게 플레이해도록 합시다.",
            "유충 오브젝트 타이밍에 죽는 경우가 많습니다. 유충 오브젝트 타이밍에 안정적으로 플레이하도록 합시다."
        ],
        "atakhan_participation": [
            "아타칸 오브젝트 참여율이 낮습니다. 가능하다면 아타칸 오브젝트 싸움에 참가하도록 합시다.",
            "아타칸 오브젝트 참여율이 높습니다. 무리하게 아타칸 오브젝트 싸움에 참여하지 않아도 되니 다른곳에서 이득을 챙기도록 합시다."
        ],
        "atakhan_deaths": [
            "아타칸 오브젝트 타이밍에 너무 안정적으로 플레이합니다. 죽더라도 오브젝트를 챙기면 이득이기에 과감하게 플레이해도록 합시다.",
            "아타칸 오브젝트 타이밍에 죽는 경우가 많습니다. 사이드 운영이나 시야 체크를 안정적으로 하도록 합시다."
        ]
    }

    # positive 적용
    for feat in positive:
        f = feat["feature"]
        coef = feat.get("coef", 1)
        if f in positive_feedback_dict:
            feedback["positive"].append(positive_feedback_dict[f][0 if coef > 0 else 1])

    # negative 적용
    for feat in negative:
        f = feat["feature"]
        coef = feat.get("coef", 1)
        if f in negative_feedback_dict:
            feedback["negative"].append(negative_feedback_dict[f][0 if coef > 0 else 1])

    return feedback







def create_comment(blue_result, red_result, tier, team):
    exclude_keys = {
        "match_id", "my_champion", "enemy_champion", "teamposition", "win", "player", "not_enough_matches",
        "early_trade_result_3min", "early_trade_result_8min", "need_recall_8min",
        "lane_cs_diff_10min", "lane_cs_result_10min", "gold_diff_10min", "lane_gold_result_10min",
        "gold_diff_14min", "midgame_gold_result",
        "my_jungle", "opp_jungle", "enemy_jungle", "top_jungle", "bot_jungle", "TOP", "MID", "BOT", "OTHER",
        "kills", "deaths", "assists", "early_kills", "early_deaths", "early_assists", "lane_cs", "kill_participation", "turret_damage",
        "team_Dragon_kills", "team_Horde_kills", "team_riftHerald_kills", "team_Baron_kills", "team_ElderDragon_kills", "team_Atakhan_kills"
    }

    # 팀 기준으로 우리팀/상대팀 매핑
    def get_team_stats(blue_result, red_result, team):
        if team == "blue":
            return blue_result, red_result
        else:
            return red_result, blue_result

    # 승률 계산
    def winrate_calc(result, tier):
        model_path = os.path.join(DATA_DIR, f"model_{result['player']['lane'].lower()}_{tier.upper()}.pkl")
        scaler_path = os.path.join(DATA_DIR, f"scaler_{result['player']['lane'].lower()}_{tier.upper()}.pkl")

        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)

        model_input_dict = {k: v for k, v in result.items() if k not in exclude_keys}
        model_input_dict["winrate"] = 50

        feature_names = list(model_input_dict.keys())
        model_input_values = np.array([list(model_input_dict.values())])
        model_input_scaled = scaler.transform(model_input_values)

        predicted_winrate = model.predict_proba(model_input_scaled)[0][1]

        coefs = model.coef_[0]
        contributions = model_input_scaled[0] * coefs

        below_avg = []
        for i, f in enumerate(feature_names):
            scaled_value = model_input_scaled[0][i]
            coef = coefs[i]
            if (coef > 0 and scaled_value < 0) or (coef < 0 and scaled_value > 0):
                below_avg.append({"feature": f, "value": model_input_dict[f], "contribution": contributions[i], "coef": coefs[i]})

        feature_contribs = [{"feature": f, "value": model_input_dict[f], "contribution": contributions[i], "coef": coefs[i]} 
                            for i, f in enumerate(feature_names)]
        sorted_features = sorted(feature_contribs, key=lambda x: x['contribution'], reverse=True)
        positive = sorted_features[:3]
        negative = sorted_features[-3:]
        positive_features = {x['feature'] for x in positive}
        below_avg = [b for b in below_avg if b['feature'] not in positive_features]

        comments = generate_feedback(positive, negative, below_avg)

        return {
            "predicted_winrate": float(predicted_winrate),
            "positive": positive,
            "negative": negative,
            "below_avg": below_avg,
            "comments": comments
        }

    # 값 비교
    def compare_value(a, b, thresholds=(0.2, -0.2)):
        upper, lower = thresholds
        if a - b > upper:
            return "유리"
        elif a - b < lower:
            return "불리"
        else:
            return "비등"

    # 정글 영역 피드백
    def area_feedback(top_count, bot_count, entity_name):
        if top_count > bot_count:
            return f"{entity_name}은 주로 탑쪽 정글에서 활동합니다."
        elif top_count < bot_count:
            return f"{entity_name}은 주로 바텀쪽 정글에서 활동합니다."
        else:
            return f"{entity_name}은 탑과 바텀 모두를 돌아다닙니다."

    # 라인별 갱 통계/summary
    def lane_summary(feedback_dict, blue, red, lane_keys=("TOP","MID","BOT","OTHER")):
        for lane in lane_keys:
            feedback_dict[lane].append(f"상대 라이너는 {lane}에서 평균 {red[lane][0]}킬, {red[lane][1]}데스를 기록했습니다.")
            feedback_dict[lane].append(f"아군 라이너는 {lane}에서 평균 {blue[lane][0]}킬, {blue[lane][1]}데스를 기록했습니다.")
        return feedback_dict

    # 🟢 팀별 승률 계산
    blue_feedback = winrate_calc(blue_result, tier)
    red_feedback = winrate_calc(red_result, tier)

    my_team, opp_team = get_team_stats(blue_result, red_result, team)

    # 🟢 비교/피드백 생성
    if my_team["player"]["lane"] not in ("JUNGLE", "UTILITY"):
        comparisons = {k: [] for k in ["early_trade_result_3min", "early_trade_result_8min", "need_recall_8min",
                                       "lane_cs_result_10min", "lane_gold_result_10min", "midgame_gold_result",
                                       "jungle", "TOP", "MID", "BOT", "OTHER"]}
        numeric_keys = ["early_trade_result_3min", "early_trade_result_8min",
                        "lane_cs_result_10min", "lane_gold_result_10min", "midgame_gold_result"]
        desc_map = {
            "early_trade_result_3min": "라인전 초반 딜교",
            "early_trade_result_8min": "라인전 중반 딜교",
            "lane_cs_result_10min": "라인전 중반 cs",
            "lane_gold_result_10min": "라인전 중반 골드",
            "midgame_gold_result": "게임 중반 골드"
        }
        for key in numeric_keys:
            result = compare_value(my_team[key], opp_team[key])
            comparisons[key].append(f"{desc_map[key]}에서 {result}할 확률이 높습니다.")

        if my_team['need_recall_8min'] < 0.5:
            comparisons['need_recall_8min'].append("8분 오브젝트 타이밍에 정비 혹은 체력 관리가 필요해보입니다.")

        # jungler 통계
        comparisons['jungle'].append(
            f"아군 라이너 최근 10게임 갱으로 {my_team['opp_jungle']}번 죽고, {my_team['my_jungle']}번 킬을 했습니다 "
        )
        comparisons['jungle'].append(
            f"적 라이너 최근 10게임 갱으로 {opp_team['opp_jungle']}번 죽고, {opp_team['my_jungle']}번 킬을 했습니다."
        )

        comparisons = lane_summary(comparisons, my_team, opp_team)

    else:
        # 정글/유틸
        comparisons = {k: [] for k in ["Enemy Area", "My Area", "TOP", "MID", "BOT", "OTHER"]}
        comparisons["My Area"].append(
            f"적은 우리 정글에 {opp_team['enemy_jungle']}번 들어왔습니다."
        )
        comparisons["Enemy Area"].append(
            f"아군은 상대 정글에 {my_team['enemy_jungle']}번 들어갔습니다."
        )
        comparisons['jungle'] = []
        comparisons['jungle'].append(area_feedback(opp_team["top_jungle"], opp_team["bot_jungle"], "적"))
        comparisons['jungle'].append(area_feedback(my_team["top_jungle"], my_team["bot_jungle"], "아군"))
        comparisons = lane_summary(comparisons, my_team, opp_team)

    # 🏆 승률 계산
    if team == "blue":
        winrate = blue_feedback["predicted_winrate"] / (blue_feedback["predicted_winrate"] + red_feedback["predicted_winrate"])
    else:
        winrate = red_feedback["predicted_winrate"] / (blue_feedback["predicted_winrate"] + red_feedback["predicted_winrate"])


    return {
        "blue": {"player": blue_result['player'], "feedback": blue_feedback},
        "red": {"player": red_result['player'], "feedback": red_feedback},
        "comparisons": comparisons,
        "winrate": winrate
    }



