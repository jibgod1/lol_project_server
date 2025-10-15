# %%
import sqlite3
import os
def create_match_db():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    db_path = os.path.join(DATA_DIR, "match_data.db")

    if os.path.exists(db_path):
        os.remove(db_path)

    tiers = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND"]
    # DB 연결 (없으면 생성됨)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for tier in tiers:
        table_name = f"match_id_{tier}"
        # 테이블 생성 (한 번만 실행하면 됨)
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name}(
            match_id TEXT,
            teamposition TEXT,ql
            my_champion TEXT,
            enemy_champion TEXT,
            kills INTEGER,
            deaths INTEGER,
            assists INTEGER,
            early_kills INTEGER,
            early_deaths INTEGER,
            early_assists INTEGER,
            diff_early_k INTEGER,
            diff_early_d INTEGER,
            diff_early_a INTEGER,
            diff_lane_cs INTEGER,
            late_kills INTEGER,
            late_deaths INTEGER,
            late_assists INTEGER,
            solo_kills INTEGER,
            kill_participation INTEGER,
            lane_cs INTEGER,
            enemyjungleminionkills INTEGER,
            vision_score INTEGER,
            wards_placed INTEGER,
            turret_damage INTEGER,
            team_Dragon_kills INTEGER,
            team_Horde_kills INTEGER,
            team_riftHerald_kills INTEGER,
            team_Baron_kills INTEGER,
            team_ElderDragon_kills INTEGER,
            team_Atakhan_kills INTEGER,
            dragon_participation INTEGER,
            dragon_deaths INTEGER,
            elder_dragon_participation INTEGER,
            elder_dragon_deaths INTEGER,
            baron_nashor_participation INTEGER,
            baron_nashor_deaths INTEGER,
            riftherald_participation INTEGER,
            riftherald_deaths INTEGER,
            horde_participation INTEGER,
            horde_deaths INTEGER,
            atakhan_participation INTEGER,
            atakhan_deaths INTEGER,
            win INTEGER,
            PRIMARY KEY (match_id, teamposition)
        )
        ''')
    conn.commit()


# %%
import sqlite3
import json
import os

def create_champion_db():
    # ------------------------------
    # 경로 설정
    # ------------------------------
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)

    db_path = os.path.join(DATA_DIR, "champion_data.db")
    json_path = os.path.join(DATA_DIR, "champion.json")

    # ------------------------------
    # DB 연결 및 테이블 생성
    # ------------------------------
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS champion (
        champ_name TEXT,
        champ_name_KR TEXT,
        champ_tags TEXT,
        champ_key INT,
        PRIMARY KEY (champ_key)
    )
    ''')
    conn.commit()

    # ------------------------------
    # JSON 파일 로드
    # ------------------------------
    if not os.path.exists(json_path):
        print(f"❌ JSON 파일이 존재하지 않습니다: {json_path}")
        conn.close()
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    champions = data.get("data", {})

    # ------------------------------
    # 데이터 삽입
    # ------------------------------
    inserted = 0
    for champ in champions.values():
        champ_name_en = champ.get("id", "")
        champ_name_kr = champ.get("name", "")
        champ_tags = ",".join(champ.get("tags", []))
        champ_key = int(champ.get("key", 0))

        cursor.execute('''
            INSERT OR REPLACE INTO champion (champ_name, champ_name_KR, champ_tags, champ_key)
            VALUES (?, ?, ?, ?)
        ''', (champ_name_en, champ_name_kr, champ_tags, champ_key))
        inserted += 1

    conn.commit()
    conn.close()

    print(f"✅ 챔피언 데이터를 DB에 저장했습니다. (총 {inserted}개)")



