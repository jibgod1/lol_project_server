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

    # positive 피드백
    for feat in positive:
        f = feat["feature"]
        coef = feat.get("coef", 1)
        if f == "diff_early_k":
            if coef > 0:
                feedback["positive"].append("라인전에서 킬 우위를 점할때가 많습니다.")
            else:
                feedback["positive"].append("팀원의 성장을 위해 킬을 양보했습니다.")
        elif f == "diff_early_d":
            if coef > 0:
                feedback["positive"].append("추반 적절한 희생으로 팀원대신 사망하여 팀원의 성장을 도왔습니다.")
            else:
                feedback["positive"].append("라인전에서의 데스가 낮습니다. 상대의 성장을 효과적으로 억제했습니다.")
        elif f == "diff_early_a":
            if coef > 0:
                feedback["positive"].append("초반 교전에서 어시스트를 통해 이득을 취했습니다.")
            else:
                feedback["positive"].append("초반 교전을 피함으로서 후반을 도모했습니다.")
        elif f == "diff_lane_cs":
            if coef > 0:
                feedback["positive"].append("견재를 통해 cs차이로 성장차이를 효과적으로 벌렸습니다.")
            else:
                feedback["positive"].append("팀원에게 cs를 양보하여 팀원의 성장을 도왔습니다.")
        elif f == "late_kills":
            if coef > 0:
                feedback["positive"].append("중후반 교전에서 킬을 통해 효과적으로 성장했습니다.")
            else:
                feedback["positive"].append("중후반 교전에서 킬 양보를 통해 팀원 성장에 기여했습니다.")
        elif f == "late_deaths":
            if coef > 0:
                feedback["positive"].append("중후반 교전에서 팀원 대신 희생하여 팀을 승리로 이끌었습니다")
            else:
                feedback["positive"].append("중후반 교전에서 잘 생존하여 팀을 승리로 이끌었습니다.")
        elif f == "late_assists":
            if coef > 0:
                feedback["positive"].append("중후반 교전에서 어시스트를 통해 팀원의 성장을 도왔습니다.")
            else:
                feedback["positive"].append("중후반 교전보다는 운영을 통해 승리를 쟁취했습니다.")
        elif f == "solo_kills":
            if coef > 0:
                feedback["positive"].append("1대1 상황에서 상대를 제압했습니다.")
            else:
                feedback["positive"].append("1대1 상황을 피하며 운영했습니다.")
        elif f == "enemyjungleminionkills":
            if coef > 0:
                feedback["positive"].append("상대 정글을 빼먹으며 효과적으로 성장했습니다.")
            else:
                feedback["positive"].append("상대 정글에 들어가지 않으며 안정적으로 플레이했습니다.")
        elif f == "vision_score":
            if coef > 0:
                feedback["positive"].append("상대의 위치를 잘 파악할 수 있도록 와드를 설치했습니다.")
            else:
                feedback["positive"].append("와드구매보다는 성장에 집중했습니다.")
        elif f == "wards_placed":
            if coef > 0:
                feedback["positive"].append("와드 쿨타임마다 와드를 설치했습니다.")
            else:
                feedback["positive"].append("시야 확보를 위한 무리한 와딩을 지양했습니다.")
        elif f == "dragon_participation":
            if coef > 0:
                feedback["positive"].append("드래곤 오브젝트에 적극적으로 참여했습니다.")
            else:
                feedback["positive"].append("드래곤 오브젝트에 집착하지 않고 다른곳에서 이득을 취했습니다.")
        elif f == "dragon_deaths":
            if coef > 0:
                feedback["positive"].append("드래곤 오브젝트 타이밍에 어그로를 끌며 팀원이 이득을 볼 수 있도록 도와주었습니다.")
            else:
                feedback["positive"].append("드래곤 오브젝트 타이밍에 죽지 않고 안정적이 플레이를 보여주었습니다.")
        elif f == "elder_dragon_participation":
            if coef > 0:
                feedback["positive"].append("장로 드래곤 오브젝트에 적극적으로 참여했습니다.")
            else:
                feedback["positive"].append("장로 드래곤 오브젝트에 집착하지 않고 다른곳에서 이득을 취했습니다.")
        elif f == "elder_dragon_deaths":
            if coef > 0:
                feedback["positive"].append("장로 드래곤 오브젝트 타이밍에 어그로를 끌며 팀원이 이득을 볼 수 있도록 도와주었습니다.")
            else:
                feedback["positive"].append("장로 드래곤 오브젝트 타이밍에 죽지 않고 안정적이 플레이를 보여주었습니다.")
        elif f == "baron_nashor_participation":
            if coef > 0:
                feedback["positive"].append("바론 오브젝트에 적극적으로 참여했습니다.")
            else:
                feedback["positive"].append("바론 오브젝트에 집착하지 않고 다른곳에서 이득을 취했습니다.")
        elif f == "baron_nashor_deaths":
            if coef > 0:
                feedback["positive"].append("바론 오브젝트 타이밍에 어그로를 끌며 팀원이 이득을 볼 수 있도록 도와주었습니다.")
            else:
                feedback["positive"].append("바론 오브젝트 타이밍에 죽지 않고 안정적이 플레이를 보여주었습니다.")
        elif f == "riftherald_participation":
            if coef > 0:
                feedback["positive"].append("전령 오브젝트에 적극적으로 참여했습니다.")
            else:
                feedback["positive"].append("전령 오브젝트에 집착하지 않고 다른곳에서 이득을 취했습니다.")
        elif f == "riftherald_deaths":
            if coef > 0:
                feedback["positive"].append("전령 오브젝트 타이밍에 어그로를 끌며 팀원이 이득을 볼 수 있도록 도와주었습니다.")
            else:
                feedback["positive"].append("전령 오브젝트 타이밍에 죽지 않고 안정적이 플레이를 보여주었습니다.")
        elif f == "horde_participation":
            if coef > 0:
                feedback["positive"].append("유충 오브젝트에 적극적으로 참여했습니다.")
            else:
                feedback["positive"].append("유충 오브젝트에 집착하지 않고 다른곳에서 이득을 취했습니다.")
        elif f == "horde_deaths":
            if coef > 0:
                feedback["positive"].append("유충 오브젝트 타이밍에 어그로를 끌며 팀원이 이득을 볼 수 있도록 도와주었습니다.")
            else:
                feedback["positive"].append("유충 오브젝트 타이밍에 죽지 않고 안정적이 플레이를 보여주었습니다.")
        elif f == "atakhan_participation":
            if coef > 0:
                feedback["positive"].append("아타칸 오브젝트에 적극적으로 참여했습니다.")
            else:
                feedback["positive"].append("아타칸 오브젝트에 집착하지 않고 다른곳에서 이득을 취했습니다.")
        elif f == "atakhan_deaths":
            if coef > 0:
                feedback["positive"].append("아타칸 오브젝트 타이밍에 어그로를 끌며 팀원이 이득을 볼 수 있도록 도와주었습니다.")
            else:
                feedback["positive"].append("아타칸 오브젝트 타이밍에 죽지 않고 안정적이 플레이를 보여주었습니다.")

    # negative 피드백
    for feat in negative:
        f = feat["feature"]
        coef = feat.get("coef", 1)
        if f == "diff_early_k":
            if coef > 0:
                feedback["negative"].append("라인전에서 킬을 많이 못먹어 불리한 상황이 많습니다.")
            else:
                feedback["negative"].append("가능하다면 라인전에서 킬을 먹기보다는 양보해주는게 좋습니다.")
        elif f == "diff_early_d":
            if coef > 0:
                feedback["negative"].append("팀원을 위해 희생하는게 좋을때도 있습니다. 나의 죽음으로 팀원들을 살릴수 있다면 여러명을 살리는 방향을 택하도록 합시다.")
            else:
                feedback["negative"].append("라인전 데스가 높은편입니다. 킬각을 인지하고 위험할때는 귀한을 하도록 합시다.")
        elif f == "diff_early_a":
            if coef > 0:
                feedback["negative"].append("초반 교전 참여율이 낮습니다. 로밍이나 정글을 적극적으로 도와봅시다.")
            else:
                feedback["negative"].append("킬 양보가 과도하여 본인 성장이 늦어졌습니다.")
        elif f == "diff_lane_cs":
            if coef > 0:
                feedback["negative"].append("라인전 cs차이가 많이납니다. 불리하더라고 라인관리를 통해 최대한 cs를 챙기도록 합시다.")
            else:
                feedback["negative"].append("라인전 cs가 너무 높습니다. cs 양보를 통해 팀원 성장을 도와주도록 합시다.")
        elif f == "late_kills":
            if coef > 0:
                feedback["negative"].append("중후반 킬이 낮습니다. 적절한 교전 참여와 킬 캐치로 성장을 하도록 합시다.")
            else:
                feedback["negative"].append("중후반 킬이 높습니다. 킬 양보를 통해 다른 팀원의 성장을 돕도록 합시다.")
        elif f == "late_deaths":
            if coef > 0:
                feedback["negative"].append("중후반 데스가 적습니다. 팀원을 살릴수 있다면 적극적으로 싸워 팀원들 살리고 대신 죽도록 합시다.")
            else:
                feedback["negative"].append("중후반 데스가 많습니다. 맵리딩을 통해 상대 위치를 예측하고 위험한 곳은 팀원과 같이 행동하도록 합시다.")
        elif f == "late_assists":
            if coef > 0:
                feedback["negative"].append("중후반 어시스트가 적습니다. 교전 참여를 통해 어시스트를 올리고 싸움에서 승리할 수 있도록 합시다.")
            else:
                feedback["negative"].append("중후반 어시스트가 많습니다. 교전 참여보다는 운영을 통해 게임을 풀어갈 수 있도록 합시다.")
        elif f == "solo_kills":
            if coef > 0:
                feedback["negative"].append("솔로킬이 적습니다. 1대1 상황에서 이길수 있을거같다면 적극적으로 싸워보도록 합시다.")
            else:
                feedback["negative"].append("1대1 상황이 많습니다. 팀원들과 같이 행동하고 가능하면 킬을 양보하도록 합시다.")
        elif f == "enemyjungleminionkills":
            if coef > 0:
                feedback["negative"].append("상대 정글몹을 거의 신경쓰지 않고있습니다. 가능하다면 상대 정글을 빼먹으며 성장하도록 합시다.")
            else:
                feedback["negative"].append("상대 정글몹에 너무 신경을 많이쓰고 있습니다. 상대 정글을 들어가기 보다는 우리 정글에서 안정적으로 플레이 하도록 합시다.")
        elif f == "vision_score":
            if coef > 0:
                feedback["negative"].append("시야 점수가 낮습니다. 적절한 위치에 와딩을 통해 상대방 위치를 파악하도록 합시다.")
            else:
                feedback["negative"].append("시야 점수가 높습니다. 와딩을 위해 너무 많은 골드를 소모하지 않도록 합시다.")
        elif f == "wards_placed":
            if coef > 0:
                feedback["negative"].append("와드를 많이 사용하지 않습니다. 장신구 와들 배치를 소홀히 하지 않도록 합시다.")
            else:
                feedback["negative"].append("너무 많은 와드를 사용하고 있습니다. 와드를 남용하지 말고 와드를 구매하는데 너무 많은 골드를 소모하지 않도록 합시다.")
        elif f == "dragon_participation":
            if coef > 0:
                feedback["negative"].append("드래곤 오브젝트 참여율이 낮습니다. 가능하다면 드래곤 오브젝트 싸움에 참가하도록 합시다.")
            else:
                feedback["negative"].append("드래곤 오브젝트 참여율이 높습니다. 무리하게 드래곤 오브젝트 싸움에 참여하지 않아도 되니 다른곳에서 이득을 챙기도록 합시다.")
        elif f == "dragon_deaths":
            if coef > 0:
                feedback["negative"].append("드래곤 오브젝트 타이밍에 너무 안정적으로 플레이합니다. 죽더라도 오브젝트를 챙기면 이득이기에 과감하게 플레이해도록 합시다.")
            else:
                feedback["negative"].append("드래곤 오브젝트 타이밍에 죽는 경우가 많습니다. 드래곤 오브젝트 타이밍에 안정적으로 플레이하도록 합시다.")
        elif f == "elder_dragon_participation":
            if coef > 0:
                feedback["negative"].append("장로 드래곤 오브젝트 참여율이 낮습니다. 가능하다면 장로 드래곤 오브젝트 싸움에 참가하도록 합시다.")
            else:
                feedback["negative"].append("장로 드래곤 오브젝트 참여율이 높습니다. 무리하게 장로 드래곤 오브젝트 싸움에 참여하지 않아도 되니 다른곳에서 이득을 챙기도록 합시다.")
        elif f == "elder_dragon_deaths":
            if coef > 0:
                feedback["negative"].append("장로 드래곤 오브젝트 타이밍에 너무 안정적으로 플레이합니다. 죽더라도 오브젝트를 챙기면 이득이기에 과감하게 플레이해도록 합시다.")
            else:
                feedback["negative"].append("장로 드래곤 오브젝트 타이밍에 죽는 경우가 많습니다. 드래곤 오브젝트 타이밍에 안정적으로 플레이하도록 합시다.")
        elif f == "baron_nashor_participation":
            if coef > 0:
                feedback["negative"].append("바론 오브젝트 참여율이 낮습니다. 가능하다면 바론 오브젝트 싸움에 참가하도록 합시다.")
            else:
                feedback["negative"].append("바론 오브젝트 참여율이 높습니다. 무리하게 바론 오브젝트 싸움에 참여하지 않아도 되니 다른곳에서 이득을 챙기도록 합시다.")
        elif f == "baron_nashor_deaths":
            if coef > 0:
                feedback["negative"].append("바론 오브젝트 타이밍에 너무 안정적으로 플레이합니다. 죽더라도 오브젝트를 챙기면 이득이기에 과감하게 플레이해도록 합시다.")
            else:
                feedback["negative"].append("바론 오브젝트 타이밍에 죽는 경우가 많습니다. 사이드 운영이나 시야 체크를 안정적으로 하도록 합시다.")
        elif f == "riftherald_participation":
            if coef > 0:
                feedback["negative"].append("전령 오브젝트 참여율이 낮습니다. 가능하다면 전령 오브젝트 싸움에 참가하도록 합시다.")
            else:
                feedback["negative"].append("전령 오브젝트 참여율이 높습니다. 무리하게 전령 오브젝트 싸움에 참여하지 않아도 되니 다른곳에서 이득을 챙기도록 합시다.")
        elif f == "riftherald_deaths":
            if coef > 0:
                feedback["negative"].append("전령 오브젝트 타이밍에 너무 안정적으로 플레이합니다. 죽더라도 오브젝트를 챙기면 이득이기에 과감하게 플레이해도록 합시다.")
            else:
                feedback["negative"].append("전령 오브젝트 타이밍에 죽는 경우가 많습니다. 전령 오브젝트 타이밍에 안정적으로 플레이하도록 합시다.")
        elif f == "horde_participation":
            if coef > 0:
                feedback["negative"].append("유충 오브젝트 참여율이 낮습니다. 가능하다면 드래곤 오브젝트 싸움에 참가하도록 합시다.")
            else:
                feedback["negative"].append("유충 오브젝트 참여율이 높습니다. 무리하게 유충 오브젝트 싸움에 참여하지 않아도 되니 다른곳에서 이득을 챙기도록 합시다.")
        elif f == "horde_deaths":
            if coef > 0:
                feedback["negative"].append("유충 오브젝트 타이밍에 너무 안정적으로 플레이합니다. 죽더라도 오브젝트를 챙기면 이득이기에 과감하게 플레이해도록 합시다.")
            else:
                feedback["negative"].append("유충 오브젝트 타이밍에 죽는 경우가 많습니다. 유충 오브젝트 타이밍에 안정적으로 플레이하도록 합시다.")
        elif f == "atakhan_participation":
            if coef > 0:
                feedback["negative"].append("아타칸 오브젝트 참여율이 낮습니다. 가능하다면 아타칸 오브젝트 싸움에 참가하도록 합시다.")
            else:
                feedback["negative"].append("아타칸 오브젝트 참여율이 높습니다. 무리하게 아타칸 오브젝트 싸움에 참여하지 않아도 되니 다른곳에서 이득을 챙기도록 합시다.")
        elif f == "atakhan_deaths":
            if coef > 0:
                feedback["negative"].append("아타칸 오브젝트 타이밍에 너무 안정적으로 플레이합니다. 죽더라도 오브젝트를 챙기면 이득이기에 과감하게 플레이해도록 합시다.")
            else:
                feedback["negative"].append("아타칸 오브젝트 타이밍에 죽는 경우가 많습니다. 사이드 운영이나 시야 체크를 안정적으로 하도록 합시다.")

    # below_avg 피드백
    for feat in below_avg:
        f = feat["feature"]
        coef = feat.get("coef", 1)
        if f == "diff_early_k":
            if coef > 0:
                feedback["below_avg"].append("라인전 킬 차이가 평균보다 높습니다. 라인전 뿐만 아니라 정글 교전, 로밍을 통해 상대방이 성장할 수 있으니 조심하도록 합시다.")
            else:
                feedback["below_avg"].append("라인전 킬 차이가 평균보다 높습니다. 과한 로밍과 정글 개입은 오히려 악영향을 미칠 수 있습니다.")
        elif f == "diff_early_d":
            if coef > 0:
                feedback["below_avg"].append("라인전 데스 차이가 평균보다 낮습니다. 죽더라도 킬을 하면 이득이라 판단되면 적극적으로 킬을 노려보도록 합시다.")
            else:
                feedback["below_avg"].append("라인전 데스 차이가 평균보다 높습니다. 라인전에서 킬각을 조심하고, 로밍, 정글에 들어갈때도 안전하게 플레이하도록 합시다.")
        elif f == "diff_early_a":
            if coef > 0:
                feedback["below_avg"].append("라인전 어시스트 차이가 평균보다 높습니다. 교전 참여를 통해 어시스트, 혹은 킬까지 노려보도록 합시다.")
            else:
                feedback["below_avg"].append("라인전 어시스트 차이가 평균보다 높습니다. 과한 로밍, 정글 개입은 오히려 악영향을 미칠 수 있습니다.")
        # elif f == "diff_lane_cs":
        #     if coef > 0:
        #         feedback["below_avg"].append("라인전 cs차이가 평균보다 높습니다. 라인 관리 능력, cs를 먹는 능력 등이 부족해 보입니다." )
        #     else:
        #         feedback["below_avg"].append("라인전 cs차이가 평균보다 높습니다. 자신의 성장만 신경쓰기 보다는 팀원의 성장에 조금 더 신경 쓰는게 좋아보입니다.")
        elif f == "late_kills":
            if coef > 0:
                feedback["below_avg"].append("중후반 킬이 평균보다 낮습니다. 중후반 교전 합류와 교전에서의 킬캐치에 좀더 신경쓰도록 합시다. ")
            else:
                feedback["below_avg"].append("중후반 킬이 평균보다 높습니다. 교전에서 킬을 전부 먹기보다는 팀원에게 양보해 같이 성장할 수 있도록 합시다.")
        elif f == "late_deaths":
            if coef > 0:
                feedback["below_avg"].append("중후반 데스가 평균보다 낮습니다. 교전 중 죽어도 이득을 볼 수 있는 경우도 있고,"
                                             "누군가는 죽어야 하는 상황도 있습니다. 누군가 죽어야 한다면 희생하는것도 생각해봅시다.")
            else:
                feedback["below_avg"].append("중후반 데스가 평균보다 높습니다. 중후반 교전에서의 데스는 경기에 큰 영향을 주기에 조금더 신중하게 플레이하도록 합시다.")
        elif f == "late_assists":
            if coef > 0:
                feedback["below_avg"].append("중후반 어시스트가 낮습니다. 적극적인 교전 참여가 필요해 보입니다.")
            else:
                feedback["below_avg"].append("중후반 어시스트가 높습니다. 과한 교전보다는 안정적인 운영이 필요해 보입니다.")
        elif f == "solo_kills":
            if coef > 0:
                feedback["below_avg"].append("솔로킬이 평균보다 낮습니다. 잘 성장했을때는 적극적으로 사이드 돌파를 노려보도록 합시다.")
            else:
                feedback["below_avg"].append("솔로킬이 평균보다 높습니다. 혼자 행동하는것보다는 팀원과 같이 행동하고 킬을 양보하도록 합시다.")
        elif f == "enemyjungleminionkills":
            if coef > 0:
                feedback["below_avg"].append("상대 정글 몬스터 킬 수가 평균보다 낮습니다." 
                                             "유리한 상황에서는 상대 정글 몬스터를 먹는걸로도 격차를 더  벌리도록 합시다.")
            else:
                feedback["below_avg"].append("상대 정글 몬스터 킬 수가 평균보다 높습니다."
                                             "무리한 상대 정글 진입은 데스로 이어질 수 있으니 조심하도록 합시다.")
        elif f == "vision_score":
            if coef > 0:
                feedback["below_avg"].append("시야 점수가 평균보다 낮습니다. 장신구 와드를 자주 사용하는 습관을 들이고, 상대 시야를 지우는것도 잊지 맙시다.")
            else:
                feedback["below_avg"].append("시야 점수가 평균보다 높습니다. 시야를 위해 과한 핑크와드 사용은 성장에 악영향을 미칩니다.")
        elif f == "wards_placed":
            if coef > 0:
                feedback["below_avg"].append("와드 배치 수가 평균보다 낮습니다. 장신구 와드를 자주 사용하고 필요하다면 핑크와드도 잘 활용하도록 합시다.")
            else:
                feedback["below_avg"].append("와드 배치가 평균보다 높습니다. 성장을 미루고 핑크와드를 사는것보다는 성장을 하는게 우선입니다.")
        elif f == "dragon_participation":
            if coef > 0:
                feedback["below_avg"].append("드래곤 오브젝트 참여도가 평균보다 낮습니다. 오브젝트 교전에 적극적으로 참여하도록 합시다.")
            else:
                feedback["below_avg"].append("드래곤 오브젝트 참여도가 평균보다 높습니다. 오브젝트 교전에 너무 집착하지 않도록 합시다.")
        elif f == "dragon_deaths":
            if coef > 0:
                feedback["below_avg"].append("드래곤 오브젝트 타이밍 데스가 평균보다 낮습니다. 적극적으로 교전에 참여하고 필요하다면 팀을 위해 희생하는 것도 생각합시다.")
            else:
                feedback["below_avg"].append("드래곤 오브젝트 타이밍 데스가 평균보다 높습니다. 오브젝트 교전 전에 죽지 않게 조심하고, 교전에서도 좀 더 신중하게 플레이 합시다.")
        elif f == "elder_dragon_participation":
            if coef > 0:
                feedback["below_avg"].append("장로 드래곤 오브젝트 참여도가 평균보다 낮습니다. 오브젝트 교전에 적극적으로 참여하도록 합시다.")
            else:
                feedback["below_avg"].append("장로 드래곤 오브젝트 참여도가 평균보다 높습니다. 오브젝트 교전에 너무 집착하지 않도록 합시다.")
        elif f == "elder_dragon_deaths":
            if coef > 0:
                feedback["below_avg"].append("장로 드래곤 오브젝트 타이밍 데스가 평균보다 낮습니다. 적극적으로 교전에 참여하고 필요하다면 팀을 위해 희생하는 것도 생각합시다.")
            else:
                feedback["below_avg"].append("장로 드래곤 오브젝트 타이밍 데스가 평균보다 높습니다. 오브젝트 교전 전에 죽지 않게 조심하고, 교전에서도 좀 더 신중하게 플레이 합시다.")
        elif f == "baron_nashor_participation":
            if coef > 0:
                feedback["below_avg"].append("바론 오브젝트 참여도가 평균보다 낮습니다. 오브젝트 교전에 적극적으로 참여하도록 합시다.")
            else:
                feedback["below_avg"].append("바론 오브젝트 참여도가 평균보다 높습니다. 오브젝트 교전에 너무 집착하지 않도록 합시다.")
        elif f == "baron_nashor_deaths":
            if coef > 0:
                feedback["below_avg"].append("바론 오브젝트 타이밍 데스가 평균보다 낮습니다. 적극적으로 교전에 참여하고 필요하다면 팀을 위해 희생하는 것도 생각합시다.")
            else:
                feedback["below_avg"].append("바론 오브젝트 타이밍 데스가 평균보다 높습니다. 오브젝트 교전 전에 죽지 않게 조심하고, 교전에서도 좀 더 신중하게 플레이 합시다.")
        elif f == "riftherald_participation":
            if coef > 0:
                feedback["below_avg"].append("전령 오브젝트 참여도가 평균보다 낮습니다. 오브젝트 교전에 적극적으로 참여하도록 합시다.")
            else:
                feedback["below_avg"].append("전령 오브젝트 참여도가 평균보다 높습니다. 오브젝트 교전에 너무 집착하지 않도록 합시다.")
        elif f == "riftherald_deaths":
            if coef > 0:
                feedback["below_avg"].append("전령 오브젝트 타이밍 데스가 평균보다 낮습니다. 적극적으로 교전에 참여하고 필요하다면 팀을 위해 희생하는 것도 생각합시다.")
            else:
                feedback["below_avg"].append("전령 오브젝트 타이밍 데스가 평균보다 높습니다. 오브젝트 교전 전에 죽지 않게 조심하고, 교전에서도 좀 더 신중하게 플레이 합시다.")
        elif f == "horde_participation":
            if coef > 0:
                feedback["below_avg"].append("유충 오브젝트 참여도가 평균보다 낮습니다. 오브젝트 교전에 적극적으로 참여하도록 합시다.")
            else:
                feedback["below_avg"].append("유충 오브젝트 참여도가 평균보다 높습니다. 오브젝트 교전에 너무 집착하지 않도록 합시다.")
        elif f == "horde_deaths":
            if coef > 0:
                feedback["below_avg"].append("유충 오브젝트 타이밍 데스가 평균보다 낮습니다. 적극적으로 교전에 참여하고 필요하다면 팀을 위해 희생하는 것도 생각합시다.")
            else:
                feedback["below_avg"].append("유충 오브젝트 타이밍 데스가 평균보다 높습니다. 오브젝트 교전 전에 죽지 않게 조심하고, 교전에서도 좀 더 신중하게 플레이 합시다.")
        elif f == "atakhan_participation":
            if coef > 0:
                feedback["below_avg"].append("아타칸 오브젝트 참여도가 평균보다 낮습니다. 오브젝트 교전에 적극적으로 참여하도록 합시다.")
            else:
                feedback["below_avg"].append("아타칸 오브젝트 참여도가 평균보다 높습니다. 오브젝트 교전에 너무 집착하지 않도록 합시다.")
        elif f == "atakhan_deaths":
            if coef > 0:
                feedback["below_avg"].append("아타칸 오브젝트 타이밍 데스가 평균보다 낮습니다. 적극적으로 교전에 참여하고 필요하다면 팀을 위해 희생하는 것도 생각합시다.")
            else:
                feedback["below_avg"].append("아타칸 오브젝트 타이밍 데스가 평균보다 높습니다. 오브젝트 교전 전에 죽지 않게 조심하고, 교전에서도 좀 더 신중하게 플레이 합시다.")

    return feedback






def create_comment(blue_result, red_result, tier, team):
    exclude_keys = {"match_id", "my_champion", "enemy_champion", "teamposition", "win", "player", "not_enough_matches",
                    "early_trade_result_3min", "early_trade_result_8min", "need_recall_8min",
                    "lane_cs_diff_10min", "lane_cs_result_10min", "gold_diff_10min", "lane_gold_result_10min", 
                    "gold_diff_14min", "midgame_gold_result",
                    "my_jungle", "opp_jungle", "enemy_jungle", "top_jungle", "bot_jungle", "TOP", "MID", "BOT", "OTHER",
                    "kills", "deaths", "assists", "early_kills", "early_deaths", "early_assists", "lane_cs", "kill_participation", "turret_damage",
                    "team_Dragon_kills", "team_Horde_kills", "team_riftHerald_kills", "team_Baron_kills", "team_ElderDragon_kills", "team_Atakhan_kills"}

    def winrate_calc(result, tier):

        model_path = os.path.join(DATA_DIR, f"model_{result['player']['lane'].lower()}_{tier.upper()}.pkl")
        scaler_path = os.path.join(DATA_DIR, f"scaler_{result['player']['lane'].lower()}_{tier.upper()}.pkl")

        model = joblib.load(model_path) 
        scaler = joblib.load(scaler_path)
    
        # 모델 입력값 준비
        model_input_dict = {k: v for k, v in result.items() if k not in exclude_keys}
        model_input_dict["winrate"] = 50   # TODO: 챔피언 승률 반영 가능
    
        feature_names = list(model_input_dict.keys())
        model_input_values = np.array([list(model_input_dict.values())])
        model_input_scaled = scaler.transform(model_input_values)
    
        # 승률 예측
        predicted_winrate = model.predict_proba(model_input_scaled)[0][1]
    
        # 각 feature 기여도 계산
        coefs = model.coef_[0]
        contributions = model_input_scaled[0] * coefs


        below_avg = []
        for i, f in enumerate(feature_names):
            scaled_value = model_input_scaled[0][i]
            coef = coefs[i]
            contribution = contributions[i]  # = scaled_value * coef
        
            if coef > 0:
                if scaled_value < 0:  # 중앙값보다 낮으면 승률에 덜 기여 → 평균 이하
                    below_avg.append({
                        "feature": f, 
                        "value": model_input_dict[f], 
                        "contribution": contribution,
                        "coef": coefs[i]
                    })
            else:  # coef < 0
                if scaled_value > 0:  # 중앙값보다 높으면 승률에 덜 기여 → 평균 이하
                    below_avg.append({
                        "feature": f,
                        "value": model_input_dict[f],
                        "contribution": contribution,
                        "coef": coefs[i]
                        })
        
        feature_contribs = []
        for i, f in enumerate(feature_names):
            feature_contribs.append({
                "feature": f,
                "value": model_input_dict[f],
                "contribution": contributions[i],
                "coef": coefs[i]
            })

    
        sorted_features = sorted(feature_contribs, key=lambda x: x['contribution'], reverse=True)
        positive = sorted_features[:3]
        negative = sorted_features[-3:]  

        positive_features = {x['feature'] for x in positive}
        below_avg = [b for b in below_avg if b['feature'] not in positive_features]
    
        # 🔹 코멘트 생성
        comments = generate_feedback(positive, negative, below_avg)
        
        print(f"\n[플레이어: {result['player']['riotId']}]")
        print("긍정 기여 Top3:", [x['feature'] for x in positive])
        print("부정 기여 Top3:", [x['feature'] for x in negative])
        print("평균 이하 지표:", [x['feature'] for x in below_avg])
        
        print("\n🔹 긍정 피드백:")
        for msg in comments['positive']:
            print("-", msg)
        
        print("\n🔹 부정 피드백:")
        for msg in comments['negative']:
            print("-", msg)
        
        print("\n🔹 평균 이하 지표 피드백:")
        for msg in comments['below_avg']:
            print("-", msg)
            
        return {
            "predicted_winrate": float(predicted_winrate),
            "positive": positive,
            "negative": negative,
            "below_avg": below_avg,
            "comments": comments
        }

    # 🔹 블루/레드 팀 결과 비교 및 리턴
    if blue_result["player"]["lane"] not in ("JUNGLE", "UTILITY"):
        if blue_result["not_enough_matches"] == True:
            blue_result["player"]["riotId"] = blue_result["player"]["riotId"] + "(정보 부족)"
        if red_result["not_enough_matches"] == True:
            red_result["player"]["riotId"] = red_result["player"]["riotId"] + "(정보 부족)"
        comparisons = {
            "early_trade_result_3min":[],
            "early_trade_result_8min":[], 
            "need_recall_8min":[],
            "lane_cs_result_10min":[], 
            "lane_gold_result_10min":[], 
            "midgame_gold_result":[],
            "jungle":[], 
            "TOP":[], "MID":[], "BOT":[], "OTHER":[],
        }
        winrate = 0 
        if team == "blue":
            blue_feedback = winrate_calc(blue_result, tier)
            red_feedback = winrate_calc(red_result, tier)
            if blue_result['early_trade_result_3min'] - red_result['early_trade_result_3min'] > 0.2:
                comparisons['early_trade_result_3min'].append("상대방 초반 딜교에서 우위를 가져갈 확률이 높습니다.")
            elif blue_result['early_trade_result_3min'] - red_result['early_trade_result_3min'] < -0.2:
                comparisons['early_trade_result_3min'].append("라인전 초반 딜교에서 불리한 확률이 높습니다.")
            else:
                comparisons['early_trade_result_3min'].append("라인전 초반 비등비등할 확률이 높습니다.")
            if blue_result['need_recall_8min'] < 0.5:
                comparisons['need_recall_8min'].append("8분 오브젝트 타이밍에 정비 혹은 체력 관리가 필요해보입니다.")
            elif blue_result['early_trade_result_8min'] - red_result['early_trade_result_8min'] > 0.2:
                comparisons['early_trade_result_8min'].append("라인전 중반 딜교에서 우위를 가져갈 확률이 높습니다.")
            elif blue_result['early_trade_result_8min'] - red_result['early_trade_result_8min'] < -0.2:
                comparisons['early_trade_result_8min'].append("라인전 중반 딜교에서 불리한 확률이 높습니다.")
            else:
                comparisons['early_trade_result_8min'].append("라인전 중반 비등비등할 확률이 높습니다.")
            if blue_result['lane_cs_result_10min'] - red_result['lane_cs_result_10min'] > 0.2:
                comparisons['lane_cs_result_10min'].append("라인전 중반 유의미한 cs차이를 낼 확률이 높습니다.")
            elif blue_result['lane_cs_result_10min'] - red_result['lane_cs_result_10min'] < -0.2:
                comparisons['lane_cs_result_10min'].append("라인전 중반 cs가 밀릴 확률이 높습니다.")
            else:
                comparisons['lane_cs_result_10min'].append("라인전 중반 cs가 비슷할 확률이 높습니다.")
            if blue_result['lane_gold_result_10min'] - red_result['lane_gold_result_10min'] > 0.2:
                comparisons['lane_gold_result_10min'].append("라인전 중반 유의미한 골드차이를 낼 확률이 높습니다.")
            elif blue_result['lane_gold_result_10min'] - red_result['lane_gold_result_10min'] < -0.2:
                comparisons['lane_gold_result_10min'].append("라인전 중반 골드가 밀릴 확률이 높습니다.")
            else:
                comparisons['lane_gold_result_10min'].append("라인전 중반 골드가 비슷할 확률이 높습니다.")
            if blue_result['midgame_gold_result'] - red_result['midgame_gold_result'] > 0.2:
                comparisons['midgame_gold_result'].append("게임 중반 유의미한 골드차이를 낼 확률이 높습니다.")
            elif blue_result['midgame_gold_result'] - red_result['midgame_gold_result'] < -0.2:
                comparisons['midgame_gold_result'].append("게임 중반 골드가 밀릴 확률이 높습니다.")
            else:
                comparisons['midgame_gold_result'].append("게임 중반 골드가 비슷할 확률이 높습니다.")
            comparisons['jungle'].append(f"최근 10게임 라인전 중 갱으로 {blue_result['opp_jungle']}번 사망했습니다.\n"
                                        f"최근 10게임 상대방 라이너는 갱으로 {red_result['my_jungle']}번 킬을 했습니다.")
            comparisons['TOP'].append(f"상대 라이너는 탑에서 평균 {red_result['TOP'][0]}킬을 기록하고 {red_result['TOP'][1]}데스를 기록했습니다.")
            comparisons['MID'].append(f"상대 라이너는 미드에서 평균 {red_result['MID'][0]}킬을 기록하고 {red_result['MID'][1]}데스를 기록했습니다.")
            comparisons['BOT'].append(f"상대 라이너는 바텀에서 평균 {red_result['BOT'][0]}킬을 기록하고 {red_result['BOT'][1]}데스를 기록했습니다.")
            comparisons['OTHER'].append(f"상대 라이너는 정글에서 평균 {red_result['OTHER'][0]}킬을 기록하고 {red_result['OTHER'][1]}데스를 기록했습니다.")
            comparisons['TOP'].append(f"아군 라이너는 탑에서 평균 {blue_result['TOP'][0]}킬을 기록하고 {blue_result['TOP'][1]}데스를 기록했습니다.")
            comparisons['MID'].append(f"아군 라이너는 미드에서 평균 {blue_result['MID'][0]}킬을 기록하고 {blue_result['MID'][1]}데스를 기록했습니다.")
            comparisons['BOT'].append(f"아군 라이너는 바텀에서 평균 {blue_result['BOT'][0]}킬을 기록하고 {blue_result['BOT'][1]}데스를 기록했습니다.")
            comparisons['OTHER'].append(f"아군 라이너는 정글에서 평균 {blue_result['OTHER'][0]}킬을 기록하고 {blue_result['OTHER'][1]}데스를 기록했습니다.")
            winrate = blue_feedback["predicted_winrate"]/(blue_feedback["predicted_winrate"]+red_feedback["predicted_winrate"])
        else:
            red_feedback = winrate_calc(red_result, tier)
            blue_feedback = winrate_calc(blue_result, tier)
            if blue_result['early_trade_result_3min'] - red_result['early_trade_result_3min'] < -0.2:
                comparisons['early_trade_result_3min'].append("라인전 초반 딜교에서 우위를 가져갈 확률이 높습니다.")
            elif blue_result['early_trade_result_3min'] - red_result['early_trade_result_3min'] > 0.2:
                comparisons['early_trade_result_3min'].append("라인전 초반 딜교에서 불리한 확률이 높습니다.")
            else:
                comparisons['early_trade_result_3min'].append("라인전 초반 비등비등할 확률이 높습니다.")
            if blue_result['need_recall_8min'] < 0.5:
                comparisons['need_recall_8min'].append("8분 오브젝트 타이밍 이전에 정비가 필요해보입니다.")
            elif blue_result['early_trade_result_8min'] - red_result['early_trade_result_8min'] < -0.2:
                comparisons['early_trade_result_8min'].append("라인전 중반 딜교에서 우위를 가져갈 확률이 높습니다.")
            elif blue_result['early_trade_result_8min'] - red_result['early_trade_result_8min'] > 0.2:
                comparisons['early_trade_result_8min'].append("라인전 중반 딜교에서 불리한 확률이 높습니다.")
            else:
                comparisons['early_trade_result_8min'].append("라인전 중반 비등비등할 확률이 높습니다.")
            if blue_result['lane_cs_result_10min'] - red_result['lane_cs_result_10min'] < -0.2:
                comparisons['lane_cs_result_10min'].append("라인전 중반 유의미한 cs차이를 낼 확률이 높습니다.")
            elif blue_result['lane_cs_result_10min'] - red_result['lane_cs_result_10min'] > 0.2:
                comparisons['lane_cs_result_10min'].append("라인전 중반 cs가 밀릴 확률이 높습니다.")
            else:
                comparisons['lane_cs_result_10min'].append("라인전 중반 cs가 비슷할 확률이 높습니다.")
            if blue_result['lane_gold_result_10min'] - red_result['lane_gold_result_10min'] < -0.2:
                comparisons['lane_gold_result_10min'].append("라인전 중반 유의미한 골드차이를 낼 확률이 높습니다.")
            elif blue_result['lane_gold_result_10min'] - red_result['lane_gold_result_10min'] > 0.2:
                comparisons['lane_gold_result_10min'].append("라인전 중반 골드가 밀릴 확률이 높습니다.")
            else:
                comparisons['lane_gold_result_10min'].append("라인전 중반 골드가 비슷할 확률이 높습니다.")
            if blue_result['midgame_gold_result'] - red_result['midgame_gold_result'] < -0.2:
                comparisons['midgame_gold_result'].append("게임 중반 유의미한 골드차이를 낼 확률이 높습니다.")
            elif blue_result['midgame_gold_result'] - red_result['midgame_gold_result'] > 0.2:
                comparisons['midgame_gold_result'].append("게임 중반 골드가 밀릴 확률이 높습니다.")
            else:
                comparisons['midgame_gold_result'].append("게임 중반 골드가 비슷할 확률이 높습니다.")
            comparisons['jungle'].append(f"최근 10게임 우리팀 라이너는 갱으로 {red_result['opp_jungle']}번 사망했습니다."
                                        f"최근 10게임 우리팀 라이너는 갱으로 {blue_result['my_jungle']}번 킬을 했습니다.")
            comparisons['TOP'].append(f"상대 라이너는 탑에서 평균 {blue_result['TOP'][0]}킬을 기록하고 {blue_result['TOP'][1]}데스를 기록했습니다.")
            comparisons['MID'].append(f"상대 라이너는 미드에서 평균 {blue_result['MID'][0]}킬을 기록하고 {blue_result['MID'][1]}데스를 기록했습니다.")
            comparisons['BOT'].append(f"상대 라이너는 바텀에서 평균 {blue_result['BOT'][0]}킬을 기록하고 {blue_result['BOT'][1]}데스를 기록했습니다.")
            comparisons['OTHER'].append(f"상대 라이너는 정글에서 평균 {blue_result['OTHER'][0]}킬을 기록하고 {blue_result['OTHER'][1]}데스를 기록했습니다.")
            comparisons['TOP'].append(f"아군 라이너는 탑에서 평균 {red_result['TOP'][0]}킬을 기록하고 {red_result['TOP'][1]}데스를 기록했습니다.")
            comparisons['MID'].append(f"아군 라이너는 미드에서 평균 {red_result['MID'][0]}킬을 기록하고 {red_result['MID'][1]}데스를 기록했습니다.")
            comparisons['BOT'].append(f"아군 라이너는 바텀에서 평균 {red_result['BOT'][0]}킬을 기록하고 {red_result['BOT'][1]}데스를 기록했습니다.")
            comparisons['OTHER'].append(f"아군 라이너는 정글에서 평균 {red_result['OTHER'][0]}킬을 기록하고 {red_result['OTHER'][1]}데스를 기록했습니다.")
            winrate = red_feedback["predicted_winrate"]/(blue_feedback["predicted_winrate"]+red_feedback["predicted_winrate"])
            
        print(blue_feedback)
        print(red_feedback)
        print(comparisons)
        print(winrate)
        return{
            "blue": {"player": blue_result['player'], "feedback": blue_feedback},
            "red": {"player": red_result['player'], "feedback": red_feedback},
            "comparisons": comparisons,
            "winrate": winrate
        }
    else:
        if blue_result["not_enough_matches"] == True:
            blue_result["player"]["riotId"] = blue_result["player"]["riotId"] + "(정보 부족)"
        if red_result['not_enough_matches'] == True:
            red_result["player"]["riotId"] = red_result["player"]["riotId"] + "(정보 부족)"
        comparisons = {
            "Enemy Area":[], "My Area":[],
            "TOP":[], "MID":[], "BOT":[], "OTHER":[],
        }
        winrate = 0 
        if team == "blue":
            blue_feedback = winrate_calc(blue_result, tier)
            red_feedback = winrate_calc(red_result, tier)
            if red_result["top_jungle"]>red_result["bot_jungle"]:
                comparisons['My Area'].append(f"상대방은 평균 {red_result['enemy_jungle']}번 우리 정글에 들어왔고 주로 탑쪽 정글에서 활동합니다.")
            elif red_result["top_jungle"]<red_result["bot_jungle"]:
                comparisons['My Area'].append(f"상대방은 평균 {red_result['enemy_jungle']}번 우리 정글에 들어왔고 주로 바텀쪽 정글에서 활동합니다.")
            else:
                comparisons['My Area'].append(f"상대방은 평균 {red_result['enemy_jungle']}번 우리 정글에 들어왔고 주로 탑과 바텀 모두를 돌아다닙니다.")
            if blue_result["top_jungle"]>blue_result["bot_jungle"]:
                comparisons['Enemy Area'].append(f"아군은 평균 {blue_result['enemy_jungle']}번 상대 정글에 들어갔고 주로 탑쪽 정글에서 활동합니다.")
            elif blue_result["top_jungle"]<blue_result["bot_jungle"]:
                comparisons['Enemy Area'].append(f"아군은 평균 {blue_result['enemy_jungle']}번 상대 정글에 들어갔고 주로 바텀쪽 정글에서 활동합니다.")
            else:
                comparisons['Enemy Area'].append(f"아군은 평균 {blue_result['enemy_jungle']}번 상대 정글에 들어갔고 탑과 바텀 모두를 돌아다닙니다.")
            comparisons['TOP'].append(f"상대 라이너는 탑에서 평균 {red_result['TOP'][0]}킬을 기록하고 {red_result['TOP'][1]}데스를 기록했습니다.")
            comparisons['MID'].append(f"상대 라이너는 미드에서 평균 {red_result['MID'][0]}킬을 기록하고 {red_result['MID'][1]}데스를 기록했습니다.")
            comparisons['BOT'].append(f"상대 라이너는 바텀에서 평균 {red_result['BOT'][0]}킬을 기록하고 {red_result['BOT'][1]}데스를 기록했습니다.")
            comparisons['OTHER'].append(f"상대 라이너는 정글에서 평균 {red_result['OTHER'][0]}킬을 기록하고 {red_result['OTHER'][1]}데스를 기록했습니다.")
            comparisons['TOP'].append(f"아군 라이너는 탑에서 평균 {blue_result['TOP'][0]}킬을 기록하고 {blue_result['TOP'][1]}데스를 기록했습니다.")
            comparisons['MID'].append(f"아군 라이너는 미드에서 평균 {blue_result['MID'][0]}킬을 기록하고 {blue_result['MID'][1]}데스를 기록했습니다.")
            comparisons['BOT'].append(f"아군 라이너는 바텀에서 평균 {blue_result['BOT'][0]}킬을 기록하고 {blue_result['BOT'][1]}데스를 기록했습니다.")
            comparisons['OTHER'].append(f"아군 라이너는 정글에서 평균 {blue_result['OTHER'][0]}킬을 기록하고 {blue_result['OTHER'][1]}데스를 기록했습니다.")
            winrate = blue_feedback["predicted_winrate"]/(blue_feedback["predicted_winrate"]+red_feedback["predicted_winrate"])
            return{
                "blue": {"player": blue_result['player'], "feedback": blue_feedback},
                "red": {"player": red_result['player'], "feedback": red_feedback},
                "comparisons": comparisons,
                "winrate": winrate
            }
        else:
            red_feedback = winrate_calc(red_result, tier)
            blue_feedback = winrate_calc(blue_result, tier)
            if blue_result["top_jungle"]>blue_result["bot_jungle"]:
                comparisons['My Area'].append(f"상대방은 평균 {blue_result['enemy_jungle']}번 우리 정글에 들어왔고 주로 탑쪽 정글에서 활동합니다.")
            elif blue_result["top_jungle"]<blue_result["bot_jungle"]:
                comparisons['My Area'].append(f"상대방은 평균 {blue_result['enemy_jungle']}번 우리 정글에 들어왔고 주로 바텀쪽 정글에서 활동합니다.")
            else:
                comparisons['My Area'].append(f"상대방은 평균 {blue_result['enemy_jungle']}번 우리 정글에 들어왔고 탑과 바텀 모두를 돌아다닙니다.")
            if red_result["top_jungle"]>red_result["bot_jungle"]:
                comparisons['Enemy Area'].append(f"아군은 평균 {red_result['enemy_jungle']}번 상대 정글에 들어갔고 주로 탑쪽 정글에서 활동합니다.")
            elif red_result["top_jungle"]<red_result["bot_jungle"]:
                comparisons['Enemy Area'].append(f"아군은 평균 {red_result['enemy_jungle']}번 상대 정글에 들어갔고 주로 바텀쪽 정글에서 활동합니다.")
            else:
                comparisons['Enemy Area'].append(f"아군은 평균 {red_result['enemy_jungle']}번 상대 정글에 들어갔고 주로 탑과 바텀 모두를 돌아다닙니다.")
            comparisons['TOP'].append(f"상대 라이너는 탑에서 평균 {blue_result['TOP'][0]}킬을 기록하고 {blue_result['TOP'][1]}데스를 기록했습니다.")
            comparisons['MID'].append(f"상대 라이너는 미드에서 평균 {blue_result['MID'][0]}킬을 기록하고 {blue_result['MID'][1]}데스를 기록했습니다.")
            comparisons['BOT'].append(f"상대 라이너는 바텀에서 평균 {blue_result['BOT'][0]}킬을 기록하고 {blue_result['BOT'][1]}데스를 기록했습니다.")
            comparisons['OTHER'].append(f"상대 라이너는 정글에서 평균 {blue_result['OTHER'][0]}킬을 기록하고 {blue_result['OTHER'][1]}데스를 기록했습니다.")
            comparisons['TOP'].append(f"아군 라이너는 탑에서 평균 {red_result['TOP'][0]}킬을 기록하고 {red_result['TOP'][1]}데스를 기록했습니다.")
            comparisons['MID'].append(f"아군 라이너는 미드에서 평균 {red_result['MID'][0]}킬을 기록하고 {red_result['MID'][1]}데스를 기록했습니다.")
            comparisons['BOT'].append(f"아군 라이너는 바텀에서 평균 {red_result['BOT'][0]}킬을 기록하고 {red_result['BOT'][1]}데스를 기록했습니다.")
            comparisons['OTHER'].append(f"아군 라이너는 정글에서 평균 {red_result['OTHER'][0]}킬을 기록하고 {red_result['OTHER'][1]}데스를 기록했습니다.")
            winrate = red_feedback["predicted_winrate"]/(blue_feedback["predicted_winrate"]+red_feedback["predicted_winrate"])
            return{
                "blue": {"player": blue_result['player'], "feedback": blue_feedback},
                "red": {"player": red_result['player'], "feedback": red_feedback},
                "comparisons": comparisons,
                "winrate": winrate
            }

        
