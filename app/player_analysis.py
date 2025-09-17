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
    ranked_queue_ids = [410, 420, 440]
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



def create_match_id_array(lane, puuids, max_match: int = 10) -> List[str]:
    api_key = config.API_KEY
    ranked_queue_ids = [410, 420, 440]
    region = 'asia'
    headers = {"X-Riot-Token": api_key}

    all_match_ids = get_match_id.get_matches_for_players(puuids, 30)
    valid_match_ids = []

    for match_id in all_match_ids:
        url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        while True:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                match_data = res.json()
                break
            elif res.status_code == 429:
                print("Rate limit... retrying in 10 seconds...")
                time.sleep(10)
            else:
                print(f"[ERROR] Match ID {match_id}: {res.status_code}")
                match_data = None
                break

        if match_data["info"].get("gameMode") != "CLASSIC" or match_data["info"].get("queueId") not in ranked_queue_ids or match_data["info"]["gameDuration"] <= 480:
            continue

        # 참가자 목록 순회해서 puuid 확인
        for participant in match_data["info"]["participants"]:
            if participant["puuid"] == puuids[0] and participant["teamPosition"].upper() == lane.upper():
                valid_match_ids.append(match_id)
                break  # 찾았으면 바로 다음 매치로

        if len(valid_match_ids) >= max_match:
            break

        time.sleep(0.05)  # 너무 짧지만 괜찮으면 유지

    # if len(valid_match_ids) < max_match:
    #     print(f"{puuids} 의 {lane} 경기 수가 적어 분석이 정확하지 않습니다 {valid_match_ids} 경기 분석함")

    return valid_match_ids

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

def player_lane(match_id, lane, puuid, match_data, match_info):
    
    my_id=0
    opp_id=0
        
    
        
    #puuid를 가진 유저와 그 상대 검색
    for player in match_data['info']['participants']:
        if player.get('teamPosition', 0) == lane:
            if player.get('puuid', 0) == puuid:
                my_id = player.get('participantId',0)
                if my_id>5:
                    opp_id = my_id-5
                else:
                    opp_id = my_id+5

    results = game_info.info(match_id, match_data, match_info, "ALL")
    my_minionkill = {}
    opp_minionkill = {}
    my_health = {}
    opp_health = {}
    my_gold = {}
    opp_gold = {}
    early_ka_situation = []
    early_d_situation = []
    my_jungle = 0
    opp_jungle = 0
    TOP = [0,0]
    MID = [0,0]
    BOT = [0,0]
    OTHER = [0,0]
    minute=0
    for frame in match_info['info']['frames']:
        timestamp = frame['timestamp']
        if 840000 <= timestamp < 900000:
            pframes = frame.get('participantFrames', {})
            my_frame = pframes.get(str(my_id), {})
            opp_frame = pframes.get(str(opp_id), {})
            my_gold[minute] = my_frame.get('totalGold')
            opp_gold[minute] = opp_frame.get('totalGold')
    
        pframes = frame.get('participantFrames', {})

        my_frame = pframes.get(str(my_id), {})
        opp_frame = pframes.get(str(opp_id), {})

     
        my_minionkill[minute] = my_frame.get("minionsKilled", 0)
        opp_minionkill[minute] = opp_frame.get("minionsKilled", 0)
        my_stats = my_frame.get('championStats') or {}
        opp_stats = opp_frame.get('championStats') or {}
        my_health[minute] = my_stats.get('health', 0)/my_stats.get('healthMax', 10000)
        opp_health[minute] = opp_stats.get('health', 0)/opp_stats.get('healthMax', 10000)
        my_gold[minute] = my_frame.get('totalGold')
        opp_gold[minute] = opp_frame.get('totalGold')
        minute=minute+1

        events = frame.get('events', [])
        for event in events:#roming check
            if event.get('type') == 'CHAMPION_KILL':
                event_timestamp = event.get('timestamp', 0)
                if event_timestamp > 840000:  # 14분 넘으면 무시
                    break
                
                killer_id = event.get('killerId')
                victim_id = event.get('victimId')
                assisting_ids = event.get('assistingParticipantIds', [])
                position = event.get('position', {})
                
                if killer_id == my_id:
                    early_ka_situation.append({
                        "killer": killer_id,
                        "victim": victim_id,
                        "assist": assisting_ids,
                        "lane": get_lane(position),
                        "time": event_timestamp
                    })
                    if 2 in assisting_ids or 6 in assisting_ids:
                        my_jungle += 1
                    match get_lane(position):
                        case "TOP":
                            TOP[0] += 1
                        case "MID":
                            MID[0] += 1
                        case "BOT":
                            BOT[0] += 1
                        case _:
                            OTHER[0] += 1
                elif my_id in assisting_ids:
                    early_ka_situation.append({
                        "killer": killer_id,
                        "victim": victim_id,
                        "assist": assisting_ids,
                        "lane": get_lane(position),
                        "time": event_timestamp
                    })
                    if 2 in assisting_ids or 6 in assisting_ids:
                        my_jungle += 1
                    match get_lane(position):
                        case "TOP":
                            TOP[0] += 1
                        case "MID":
                            MID[0] += 1
                        case "BOT":
                            BOT[0] += 1
                        case _:
                            OTHER[0] += 1
                    
                elif victim_id == my_id:
                    early_d_situation.append({
                        "killer": killer_id,
                        "victim": victim_id,
                        "assist": assisting_ids,
                        "lane": get_lane(position),
                        "time": event_timestamp
                    })
                    if 2 in assisting_ids or 6 in assisting_ids:
                        opp_jungle += 1
                    match get_lane(position):
                        case "TOP":
                            TOP[1] += 1
                        case "MID":
                            MID[1] += 1
                        case "BOT":
                            BOT[1] += 1
                        case _:
                            OTHER[1] += 1
                    

    # if my_health[3]-opp_health[3]>0.25:
    #     print("3분 딜교환 우위")
    # elif opp_health[3]-my_health[3]>0.25:
    #     print("3분 딜교환 손해")
    # else:
    #     print("3분 비등비등함")
        
    # if my_health[8] == 1:
    #     print("8분전에 정비 필요")
    # elif my_health[8]-opp_health[8]>0.25:
    #     print("8분 유리함")
    # elif opp_health[8]-my_health[8]>0.25:
    #     print("8분 불리함")
    # else:
    #     print("8분 비등비등함")
        
    # if my_minionkill[10]-opp_minionkill[10]>20:
    #     print("라인관리를 통해 이득을 많이 취함")
    # elif opp_minionkill[10]-my_minionkill[10]>20:
    #     print("라인관리 미숙으로 손해를 많이 봄")
    # else:
    #     print("라인관리 비슷함")
        
    # if my_gold[10] - opp_gold[10]>300:
    #     print("10분 라인전 유리")
    # elif opp_gold[10] - my_gold[10]>300:
    #     print("10분 라인전 불리")
    # else:
    #     print("10분 비등비등함")

    # if my_gold[14] - opp_gold[14]>300:
    #     print("게임 중반 유리")
    # elif opp_gold[14] - my_gold[14]>300:
    #     print("게임 중반 불리")
    # else:
    #     print("게임 중반 비등비등함")
        
    results[my_id].update({
        "early_trade_result_3min": (
            1 if my_health[3] - opp_health[3] > 0.25 else
            -1 if opp_health[3] - my_health[3] > 0.25 else
            0
        ),
        "early_trade_result_8min": (
            1 if my_health[8] - opp_health[8] > 0.25 else
            -1 if opp_health[8] - my_health[8] > 0.25 else
            0
        ),
        "need_recall_8min": my_health[8] == 1 or my_health[8] < 0.5,
        "lane_cs_diff_10min": my_minionkill[10] - opp_minionkill[10],
        "lane_cs_result_10min": (
            1 if my_minionkill[10] - opp_minionkill[10] > 20 else
            -1 if opp_minionkill[10] - my_minionkill[10] > 20 else
            0
        ),
        "gold_diff_10min": my_gold[10] - opp_gold[10],
        "lane_gold_result_10min": (
            1 if my_gold[10] - opp_gold[10] > 300 else
            -1 if opp_gold[10] - my_gold[10] > 300 else
            0
        ),
        "gold_diff_14min": my_gold[14] - opp_gold[14],
        "midgame_gold_result": (
            1 if my_gold[14] - opp_gold[14] > 300 else
            -1 if opp_gold[14] - my_gold[14] > 300 else
            0
        ),
        "my_jungle" : my_jungle,#우리팀 정글이 갱 온 횟수
        "opp_jungle" : opp_jungle,#상대팀 정글이 갱 온 횟수
        "TOP" : TOP,
        "MID" : MID,
        "BOT" : BOT,
        "OTHER" : OTHER,
    })
    return results[my_id]
            

def player_jungle(match_id, lane, puuid, match_data, match_info):
    print("jungle")
    

def player_util(match_id, lane, puuid, match_data, match_info):
    print("support")
   

def player_analysis(match_id, lane, puuid):
    api_key = config.API_KEY
    region = 'asia'
    
    url1 = f'https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}'
    url2 = f'https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline'

    headers = {'X-Riot-Token': api_key}

    while True:  # 🔹 무한 루프를 사용해 에러 발생 시 재시도
        response1 = requests.get(url1, headers=headers)
        response2 = requests.get(url2, headers=headers)
        if response1.status_code == 200 and response2.status_code == 200:
            match_data = response1.json()
            match_info = response2.json()
            break
        elif response1.status_code == 429 or response2.status_code == 429:
                print("Rate limit... retrying in 10 seconds...")
                time.sleep(10)
        else:
            print(f"[ERROR] Match ID {match_id}: {res.status_code}")
        
    
    # if lane == "JUNGLE":
    #     result = player_jungle(match_id, lane, puuid, match_data, match_info)
    #     return result
    # #정글러 분석-----------------------------------------------------------------
    # #라인 별 갱킹 횟수
    # #킬로 이어진 갱 시간대
    # #선호하는 오브젝트(용, 유충)
    # elif lane == "UTILITY":
    #     result = player_util(match_id, lane, puuid, match_data, match_info)
    #     return result

    # else:
    #     result = player_lane(match_id, lane, puuid, match_data, match_info)
    #     return result
    result = player_lane(match_id, lane, puuid, match_data, match_info)
    return result

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
                feedback["positive"].append("킬 양보를 통해 이득을 보는 경우가 많습니다.")
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
                feedback["negative"].append("교전 참여율, 혹은 킬 양보가 많습니다. 과한 싸움, 혹은 양보는 라인전에 불리한 영향을 미칠 수 있습니다.")
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
                feedback["negative"].append("바론 오브젝트 타이밍에 죽는 경우가 많습니다. 바론 오브젝트 타이밍에 안정적으로 플레이하도록 합시다.")
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
                feedback["negative"].append("아타칸 오브젝트 타이밍에 죽는 경우가 많습니다. 아타칸 오브젝트 타이밍에 안정적으로 플레이하도록 합시다.")

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
                feedback["below_avg"].append("라인전 데스 차이가 평균보다 낮습니다. 교전 중 죽어도 이득을 볼 수 있는 경우도 있고,"
                                             "누군가는 죽어야 하는 상황도 있습니다. 누군가 죽어야 한다면 희생하는것도 생각해봅시다.")
            else:
                feedback["below_avg"].append("라인전 데스 차이가 평균보다 높습니다. 라인전에서 킬각을 조심하고, 로밍, 정글에 들어갈때도 안전하게 플레이하도록 합시다.")
        elif f == "diff_early_a":
            if coef > 0:
                feedback["below_avg"].append("라인전 어시스트 차이가 평균보다 낮습니다. 교전 참여를 통해 어시스트, 혹은 킬까지 노려보도록 합시다.")
            else:
                feedback["below_avg"].append("라인전 어시스트 차이가 평균보다 높습니다. 과한 로밍, 정글 개입은 오히려 악영향을 미칠 수 있습니다.")
        elif f == "diff_lane_cs":
            if coef > 0:
                feedback["below_avg"].append("라인전 cs차이가 평균보다 낮습니다. 라인 관리 능력, cs를 먹는 능력 등이 부족해 보입니다." 
                                             " ai, 사용자 게임을 통해 연습을 하거나 동영상을 통해 학습을 하도록 합시다.")
            else:
                feedback["below_avg"].append("라인전 cs차이가 평균보다 높습니다. 자신의 성장만 신경쓰기 보다는 팀원의 성장에 조금 더 신경 쓰는게 좋아보입니다.")
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
                    "my_jungle", "opp_jungle", "TOP", "MID", "BOT", "OTHER",
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
            comparisons['early_trade_result_3min'].append("라인전 초반 딜교에서 우위를 가져갈 확률이 높습니다.")
        elif blue_result['early_trade_result_3min'] - red_result['early_trade_result_3min'] < -0.2:
            comparisons['early_trade_result_3min'].append("라인전 초반 딜교에서 불리한 확률이 높습니다.")
        else:
            comparisons['early_trade_result_3min'].append("라인전 초반 비등비등할 확률이 높습니다.")
        if blue_result['need_recall_8min'] < 0.5:
            comparisons['need_recall_8min'].append("8분 오브젝트 타이밍 이전에 정비가 필요해보입니다.")
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
        comparisons['jungle'].append(f"최근 10게임 라인전 중 갱으로 {red_result['opp_jungle']}번 사망했습니다."
                                     f"최근 10게임 상대방 라이너는 갱으로 {blue_result['my_jungle']}번 킬을 했습니다.")
        comparisons['TOP'].append(f"상대 라이너는 탑에서 평균 {blue_result['TOP'][0]}킬을 기록하고 {blue_result['TOP'][1]}데스를 기록했습니다.")
        comparisons['MID'].append(f"상대 라이너는 미드에서 평균 {blue_result['MID'][0]}킬을 기록하고 {blue_result['MID'][1]}데스를 기록했습니다.")
        comparisons['BOT'].append(f"상대 라이너는 바텀에서 평균 {blue_result['BOT'][0]}킬을 기록하고 {blue_result['BOT'][1]}데스를 기록했습니다.")
        comparisons['OTHER'].append(f"상대 라이너는 정글에서 평균 {blue_result['OTHER'][0]}킬을 기록하고 {blue_result['OTHER'][1]}데스를 기록했습니다.")
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

        


def game_analysis(players, lane, tier, team):
    exclude_keys1 = {"match_id", "my_champion", "enemy_champion", "teamposition", "win"}
    exclude_keys2 = {"match_id", "my_champion", "enemy_champion", "teamposition", "win", 
                     "early_trade_result_3min", "early_trade_result_8min", "need_recall_8min",
                     "lane_cs_diff_10min", "lane_cs_result_10min", "gold_diff_10min", "lane_gold_result_10min", 
                     "gold_diff_14min", "midgame_gold_result",
                     "my_jungle", "opp_jungle", "TOP", "MID", "BOT", "OTHER",
                     "kills", "deaths", "assists", "early_kills", "early_deaths", "early_assists", "lane_cs", "kill_participation", "turret_damage",
                     "team_Dragon_kills", "team_Horde_kills", "team_riftHerald_kills", "team_Baron_kills", "team_ElderDragon_kills", "team_Atakhan_kills"}
    
    blue = players[:5]
    red = players[5:]

    order_map = {
        "TOP":     [0, 1, 2, 3, 4],
        "JUNGLE":  [1, 2, 3, 4, 0],
        "MIDDLE":  [2, 1, 3, 4, 0],
        "BOTTOM":  [3, 4, 1, 2, 0],
        "UTILITY": [4, 3, 1, 2, 0],
    }

    order = order_map[lane]

    # 재배치
    players_ordered = []
    prev_result = None
    for idx in order:
        players_ordered.append(blue[idx])
        players_ordered.append(red[idx])
        
    for player in players_ordered:
        puuid = player['puuid']
        player_lane = player.get('lane')


        # 최근 경기 데이터 수집
        match_id_list = create_match_id_array(player_lane, [puuid])
        my_results = []
        for match_id in match_id_list[:10]:  # 최대 10경기
            result = player_analysis(match_id, player_lane, puuid)
            if not result:
                continue
            filtered = {k: v for k, v in result.items() if k not in exclude_keys1}
            my_results.append(filtered)

        if not my_results:
            print(f"{player['riotId']} 데이터 없음")
            continue  

        # 평균 계산
        avg_result = {}
        for key in my_results[0].keys():
            values = [r[key] for r in my_results]

            if key in {"my_jungle", "opp_jungle"}:
                avg_result[key] = sum(values)

            elif isinstance(values[0], (int, float)):
                avg_result[key] = sum(values) / len(values)

            elif isinstance(values[0], list):
                avg_result[key] = [
                    sum(v[i] for v in values) / len(values)
                    for i in range(len(values[0]))
                ]
        avg_result['player'] = player
        avg_result['not_enough_matches'] = len(match_id_list) < 10
        if prev_result is None:
            prev_result = avg_result
# 여기랑 game_info 수집하는 코드 변경 필요
        else:
            # 두 명(같은 라인) 정보 넘겨줌
            # return {
            #     "prev_result": prev_result,
            #     "avg_result": avg_result,
            #     "tier": tier,
            #     "team": team
            # }
            comment = create_comment(prev_result, avg_result, tier, team)
            print(comment)
            prev_result = None
        



# puuid = get_player_puuid.get_player_puuid("정유영", "KR2")
# players = ingame_players_id(puuid)
# players = [{'riotId': '파 멸#혼란폭력', 'puuid': '0dK3NbFT-MTqNxGMMa5Bvf1wQ64LXkrjMCw_cd84oc5tCtScbfRrS9jKEdoqjj96F9f7nkPWCVwixQ', 'lane': 'TOP'}, 
#            {'riotId': '이 드#kr0', 'puuid': '08eWvcrlhvPV9E3EY54D0OkUhPl8mdabGMLM0HYUqBtYxJdtOv8HYC3KD-8QFecJxeyBWPlSluWfUg', 'lane': 'JUNGLE'}, 
#            {'riotId': '조맹맹맹맹#4545', 'puuid': 'RgA1dDKbM7SXFirQWWKwvidVtq5L6sH681UDXtruO5qDkEGRfki_brVP58yJrqKz-WJJD9PFguRhDA', 'lane': 'MIDDLE'}, 
#            {'riotId': '비라악#KR1', 'puuid': 'c7Lan8kPys9fzR5RaKHXajv7ASYmqhdy31uZWEGgiISmwCyid2l6a06UeFjO6fzRPImsxyaxtNMy1g', 'lane': 'BOTTOM'}, 
#            {'riotId': '안참는개#0217', 'puuid': '9abbI0eWCIYIconf8RHJsT4M2hDNwoktdOzvjrSWoh4EB7Yyt33XlgCzrG2gXm15r_Pb_Yy_7pGnug', 'lane': 'UTILITY'}, 
#            {'riotId': '호떠기다#KR1', 'puuid': 'nDNgD_6Ocy9DRHVi_GbiCypOJA95hU4_T78y2I2hh0CX-kQ-k1fmaUNfMjjQZPjxJvtxdvOoiSYQzQ', 'lane': 'TOP'}, 
#            {'riotId': '정유영#KR2', 'puuid': 'pgwqD1Btfiamr2RWra1w0GQ8cL9N0qyBusPfU1hjhGw8qDplNpn4ayWmCsiZeImmC9bwoar6gDTC2w', 'lane': 'JUNGLE'}, 
#            {'riotId': '이 효 민#kr2', 'puuid': 'f93X58pGbdfPKEvn1UwPOcRFeGSguZLE4q0zzz4cpDl-qMhN6mof83qzZIs-Mc3xCGvxV74y9E8d4g', 'lane': 'MIDDLE'}, 
#            {'riotId': '내똥매우커#박잉여', 'puuid': 'X1DvD3cwAamCre4nRNcTldQE2Q6MmOD8zbmjTiEzbIvMPsiGspoux8yTU--VinR7JlAGUy9CA4sgGQ', 'lane': 'BOTTOM'}, 
#            {'riotId': '옆집누나의향기#KR1', 'puuid': 'PK5Xyk7tyfs2tuIF3wzUJmQQl6qxVslk0RYkuABA5_ux60tafETyNReCEeKUH5IVWyrx5EnnvTdGaQ', 'lane': 'UTILITY'}]
# players[0]["lane"] = "TOP"
# players[1]["lane"] = "BOTTOM"
# players[2]["lane"] = "MIDDLE"
# players[3]["lane"] = "UTILITY"
# players[4]["lane"] = "JUNGLE"
# players[5]["lane"] = "JUNGLE"
# players[6]["lane"] = "MIDDLE"
# players[7]["lane"] = "BOTTOM"
# players[8]["lane"] = "UTILITY"
# players[9]["lane"] = "TOP"
# for i, p in enumerate(players):
#     if p["puuid"] == puuid:
#         team = "blue" if i <= 4 else "red"
#         break
# current_players = players.copy()

# blue_team = current_players[:5]
# red_team = current_players[5:]

# order = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

# blue_sorted = []
# for lane in order:
#     for p in blue_team:
#         if p["lane"] == lane:
#             blue_sorted.append(p)
#             break
            
# red_sorted = []
# for lane in order:
#     for p in red_team:
#         if p["lane"] == lane:
#             red_sorted.append(p)
#             break

# players = blue_sorted + red_sorted
# print(players)
# print(team)
# print(game_analysis(players, "MIDDLE", "BRONZE", team))
# for r in game_analysis(players, "MIDDLE", "BRONZE", team):
#     print(r)

# %%