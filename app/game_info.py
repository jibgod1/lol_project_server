# %%
import requests
import time
import sqlite3
import os
import config  
import json

def game_info(match_id, tier, flag):
    api_key = config.API_KEY
    ranked_queue_ids = [410, 420, 440]
    region = 'asia'
    
    url1 = f'https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}'
    url2 = f'https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline'

    headers = {'X-Riot-Token': api_key}
    
    while True:  # 🔹 무한 루프를 사용해 429 에러 발생 시 재시도
        response1 = requests.get(url1, headers=headers)
        response2 = requests.get(url2, headers=headers)
        time.sleep(1.6)
        
        if response1.status_code == 200 and response2.status_code == 200:
            match_data = response1.json()
            match_info = response2.json()

           
            
            if match_data["info"]["gameMode"] == "CLASSIC" or match_data["info"]["queueId"] in ranked_queue_ids:
                results = info(match_id, match_data, match_info, flag)
                item_results = item_info(match_data, flag)
                save_item_to_db(item_results)
                BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                DATA_DIR = os.path.join(BASE_DIR, "data")
                db_path = os.path.join(DATA_DIR, "match_data.db")
                conn = sqlite3.connect(db_path)  # 🔸 DB 연결
                cursor = conn.cursor()                   # 🔸 커서 생성
                for row in results.values():
                    values = tuple(row.values())  # 딕셔너리 값을 튜플로 변환
                    cursor.execute(f'''
                        INSERT OR IGNORE INTO match_id_{tier} VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                    ''', values)
                
                conn.commit()
                conn.close()
                return
            else:
                print("랭크게임 혹은 일반게임이 아닙니다")
                return "NONE"
        
        elif response1.status_code == 429 or response2.status_code == 429:  # 🔹 429 오류 발생 시
            print("429 오류 발생! 10초 후 다시 시도합니다...")
            time.sleep(10)  # 🔹 10초 대기 후 다시 시도
        
        else:
            print("user_line_winrate.ipynb error")
            print(f"Error: {response1.status_code}, {response2.status_code}")
            return "NONE"

    return "NONE"



def get_opponent_map(participants):
    lane_map = {}
    for p in participants:
        team_pos = p.get("teamPosition")
        team_id = p.get("teamId")
        pid = p.get("participantId")
        if team_pos not in lane_map:
            lane_map[team_pos] = {}
        lane_map[team_pos][team_id] = pid  # teamPosition 기준으로 팀별 매핑
    opponent_map = {}
    for lane, team_dict in lane_map.items():
        if 100 in team_dict and 200 in team_dict:
            opponent_map[team_dict[100]] = team_dict[200]
            opponent_map[team_dict[200]] = team_dict[100]
    return opponent_map


def info(match_id, match_data, match_info, flag):
    opponent_map = get_opponent_map(match_data['info']['participants'])
                
    early_kda = {i: {"kills": 0, "deaths": 0, "assists": 0} for i in range(1, 11)}
    late_kda = {i: {"kills": 0, "deaths": 0, "assists": 0} for i in range(1, 11)}

    epic_monsters = ["dragon", "elder_dragon", "baron_nashor", "riftherald", "horde", "atakhan"]
    participant_stats = {}

    results = {}  # 🔹 최종 결과 저장용 리스트
    
    for i in range(1, 11):
        participant_stats[i] = {}
        for monster in epic_monsters:
            monster = monster.lower()
            participant_stats[i][f"{monster}_participation"] = 0
            participant_stats[i][f"{monster}_deaths"] = 0


    teams = match_data['info']['teams']
    team_objectives = {}
    for team in teams:
        team_objectives[team['teamId']] = team['objectives']

    # 이벤트 순회
    for frame in match_info['info']['frames']:
        for event in frame['events']:
            
            # 챔피언 킬 관련 수집
            if event.get('type') == 'CHAMPION_KILL':
                killer = event.get('killerId')
                victim = event.get('victimId')
                assists = event.get('assistingParticipantIds', [])
                timestamp = event.get('timestamp', 0)
                # 14분전 챔피언 킬
                if timestamp <= 840000:
                    if killer in early_kda:
                        early_kda[killer]["kills"] += 1
                    if victim in early_kda:
                        early_kda[victim]["deaths"] += 1
                    for assister in assists:
                        if assister in early_kda:
                            early_kda[assister]["assists"] += 1
                # 14분후 챔피언 킬
                else:
                    if killer in late_kda:
                        late_kda[killer]["kills"] += 1
                    if victim in late_kda:
                        late_kda[victim]["deaths"] += 1
                    for assister in assists:
                        if assister in late_kda:
                            late_kda[assister]["assists"] += 1

                # 에픽 몬스터 관련 킬
                pos = event.get('position', {})
                if not pos:
                    continue
                event_x = pos.get('x', -99999)
                event_y = pos.get('y', -99999)

                nearby_monsters = [
                    e for e in frame['events']
                    if e.get('type') == 'ELITE_MONSTER_KILL' and
                       e.get('monsterType', '').lower() in epic_monsters and
                       (e['timestamp'] - timestamp <= 120000 or timestamp - e['timestamp'] <= 60000)
                ]

                for monster_event in nearby_monsters:
                    monster = monster_event['monsterType'].lower()
                    if killer in participant_stats:
                        participant_stats[killer][f"{monster}_participation"] += 1
                    if victim in participant_stats:
                        participant_stats[victim][f"{monster}_deaths"] += 1
                        late_kda[victim]["deaths"] -= 1
                        if late_kda[victim]["deaths"] < 0:
                            late_kda[victim]["deaths"] = 0
                    for assister in assists:
                        if assister in participant_stats:
                            participant_stats[assister][f"{monster}_participation"] += 1

            
                        
    
    for player in match_data['info']['participants']:
        id = player.get('participantId',0)
        
        if flag=="ODD" and id % 2 == 0:
            continue  # flag=ODD인데 짝수면 저장 안함
        elif flag=="EVEN" and id % 2 != 0:
            continue  # flag=EVEN인데 홀수면 저장 안함
        teamposition = player.get('teamPosition', 0)
        kills = player.get('kills', 0)
        deaths = player.get('deaths', 0)
        assists = player.get('assists', 0)
        solo_kills = player.get('challenges', {}).get('soloKills', 0)
        kill_participation = int(player.get('challenges', {}).get('killParticipation', 0) * 100)
        lane_cs = player.get('challenges', {}).get('laneMinionsFirst10Minutes', 0)
        enemyjungleminionkills = player.get('totalEnemyJungleMinionsKilled', 0)
        vision_score = player.get('visionScore', 0)
        wards_placed = player.get('wardsPlaced', 0)
        turret_damage = player.get("damageDealtToTurrets")
        
        team_id = player.get('teamId', 0)
        team_obj = team_objectives.get(team_id, {})
        # 오브젝트 관련 값 추출
        dragon_kills = team_obj.get('dragon', {}).get('kills', 0)
        elder_dragon_kills = player.get('challenges', {}).get('teamElderDragonKills', 0)
        baron_kills = team_obj.get('baron', {}).get('kills', 0)
        rift_kills = team_obj.get('riftHerald', {}).get('kills', 0)
        horde_kills = team_obj.get('horde', {}).get('kills', 0)
        atakhan_kills = team_obj.get('atakhan', {}).get('kills', 0)
                        
        # 기본값들
        early_k = early_kda[id]["kills"]
        early_d = early_kda[id]["deaths"]
        early_a = early_kda[id]["assists"]
        lane_cs = player.get('challenges', {}).get('laneMinionsFirst10Minutes', 0)

        
        # 상대와 비교
        opp_id = opponent_map.get(id, None)

        my_champion = player.get("championName", "Unknown")
        opp_player = match_data['info']['participants'][opp_id - 1]
        enemy_champion = opp_player.get("championName", "Unknown")
        
        if opp_id:
            diff_early_k = early_k - early_kda[opp_id]["kills"]
            diff_early_d = early_d - early_kda[opp_id]["deaths"]
            diff_early_a = early_a - early_kda[opp_id]["assists"]
            diff_lane_cs = lane_cs - match_data['info']['participants'][opp_id - 1]['challenges'].get('laneMinionsFirst10Minutes', 0)
        else:
            diff_early_k = early_k
            diff_early_d = early_d
            diff_early_a = early_a
            diff_lane_cs = lane_cs
        
        if player.get('win')==True:
            win = 1
        else:
            win = 0
        
        # 🔹 결과 배열 저장
        results[id] = {
            "match_id": match_id,
            "teamposition": teamposition, 
            "my_champion": my_champion,
            "enemy_champion": enemy_champion,
            "kills": kills, 
            "deaths": deaths, 
            "assists": assists,
            "early_kills": early_k, 
            "early_deaths": early_d, 
            "early_assists": early_a,
            "diff_early_k": diff_early_k, 
            "diff_early_d": diff_early_d, 
            "diff_early_a": diff_early_a, 
            "diff_lane_cs": diff_lane_cs,
            "late_kills": late_kda[id]["kills"], 
            "late_deaths": late_kda[id]["deaths"], 
            "late_assists": late_kda[id]["assists"],
            "solo_kills": solo_kills, 
            "kill_participation": kill_participation, 
            "lane_cs": lane_cs,
            "enemyjungleminionkills": enemyjungleminionkills, 
            "vision_score": vision_score, 
            "wards_placed": wards_placed,
            "turret_damage": turret_damage,
            "team_Dragon_kills": dragon_kills, 
            "team_Horde_kills": horde_kills,
            "team_riftHerald_kills": rift_kills, 
            "team_Baron_kills": baron_kills, 
            "team_ElderDragon_kills": elder_dragon_kills,
            "team_Atakhan_kills": atakhan_kills,
            "dragon_participation": participant_stats[id]["dragon_participation"], 
            "dragon_deaths": participant_stats[id]["dragon_deaths"],
            "elder_dragon_participation": participant_stats[id]["elder_dragon_participation"], 
            "elder_dragon_deaths": participant_stats[id]["elder_dragon_deaths"],
            "baron_nashor_participation": participant_stats[id]["baron_nashor_participation"], 
            "baron_nashor_deaths": participant_stats[id]["baron_nashor_deaths"],
            "riftherald_participation": participant_stats[id]["riftherald_participation"], 
            "riftherald_deaths": participant_stats[id]["riftherald_deaths"],
            "horde_participation": participant_stats[id]["horde_participation"], 
            "horde_deaths": participant_stats[id]["horde_deaths"],
            "atakhan_participation": participant_stats[id]["atakhan_participation"],
            "atakhan_deaths": participant_stats[id]["atakhan_deaths"],
            "win": win
        }
    return results

def item_info(match_data, flag):
    results = {}

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    JSON_PATH = os.path.join(BASE_DIR, "data", "item.json")

    # JSON 읽기
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        item_data = json.load(f)

    for player in match_data['info']['participants']:
        pid = player.get('participantId', 0)
        team_id = player.get('teamId', 0)

        # 🔹 flag 조건 (블루팀 / 레드팀 구분)
        if flag == "ODD" and pid % 2 == 0:
            continue
        elif flag == "EVEN" and pid % 2 != 0:
            continue

        # 🔹 내 챔피언 역할 (리스트)
        my_roles = get_champion_roles(player.get('championName', 'Unknown'))

        # 🔹 내가 산 아이템 (최대 7개) + 2200원 이상 필터
        my_items = [player.get(f'item{i}', 0) for i in range(7)]
        my_items = [item for item in my_items if item != 0]

        # 🔹 2200원 이상 아이템만 필터링
        filtered_items = []
        total_gold = 0
        for item_id in my_items:
            item_str_id = str(item_id)
            if item_str_id in item_data["data"]:
                price = item_data["data"][item_str_id].get("gold", {}).get("total", 0)
                if price >= 2200:
                    filtered_items.append(item_id)
                    total_gold += price

        # 🔹 상대팀 역할 (각 챔피언 역할 리스트)
        enemy_roles = []
        for p in match_data['info']['participants']:
            if p.get('teamId') != team_id:
                enemy_roles.append(get_champion_roles(p.get('championName', 'Unknown')))

        # 🔹 승패 (True/False → 1/0)
        win = 1 if player.get('win') else 0

        # 🔹 결과 저장
        results[pid] = {
            "my_roles": my_roles,
            "my_items": filtered_items,   # 2200원 이상 아이템만
            "enemy_roles": enemy_roles,
            "total_gold": total_gold,     # 2200원 이상 아이템 기준
            "win": win
        }

    return results

def get_champion_roles(champ_name):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "data", "champion_data.db")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT champ_tags FROM champion WHERE champ_name = ?", (champ_name,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        tags = [tag.strip() for tag in result[0].split(",")]
        return tags
    else:
        return ["Unknown"]

def calculate_total_item_gold(my_items):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    JSON_PATH = os.path.join(BASE_DIR, "data", "item.json")

    # JSON 읽기
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        item_data = json.load(f)

    total_gold = 0
    for item_id in my_items:
        item_str_id = str(item_id)
        if item_str_id in item_data["data"]:
            item_info = item_data["data"][item_str_id]
            price = item_info.get("gold", {}).get("total", 0)
            
            if price >= 2200:
                item_name = item_info.get("name", "Unknown")
                print(f"아이템: {item_name}, 가격: {price}")
                total_gold += price
    print(f"total: {total_gold}")
    return total_gold

def save_item_to_db(results):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "data", "item_data.db")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS item_feedback (
            my_role TEXT,
            my_items TEXT,
            enemy_roles TEXT,
            total_gold INTEGER,
            win INTEGER
        )
    """)

    for pid, data in results.items():
        my_roles_str = ",".join(data["my_roles"])
        my_items_str = ",".join(map(str, data["my_items"]))
        enemy_roles_str = ";".join(["|".join(r) for r in data["enemy_roles"]])
        print(f"db total: {data['total_gold']}")
        cursor.execute("""
            INSERT INTO item_feedback
            (my_role, my_items, enemy_roles, total_gold, win)
            VALUES (?, ?, ?, ?, ?)
        """, (my_roles_str, my_items_str, enemy_roles_str, data["total_gold"], data["win"]))

    conn.commit()
    conn.close()
    print(f"{len(results)}개의 데이터가 item_data.db에 저장되었습니다.")
# %%



