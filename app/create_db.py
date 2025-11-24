# %% 
# create_match_db_mysql.py
import mysql.connector
from config import PASSWARD

def create_match_db():
    # ------------------------------
    # MySQL 서버 연결
    # ------------------------------
    mysql_config = {
        "host": "3.37.127.128",
        "user": "lol_local",
        "password": PASSWARD, 
        "database": "pick_ban_data",
        "port": 3306
    }

    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()

    tiers = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND"]

    for tier in tiers:
        table_name = f"match_id_{tier}"
        # 기존 테이블 삭제
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`;")
        # 테이블 생성
        cursor.execute(f"""
        CREATE TABLE `{table_name}` (
            match_id VARCHAR(255),
            teamposition VARCHAR(50),
            my_champion VARCHAR(100),
            enemy_champion VARCHAR(100),
            kills INT,
            deaths INT,
            assists INT,
            early_kills INT,
            early_deaths INT,
            early_assists INT,
            diff_early_k INT,
            diff_early_d INT,
            diff_early_a INT,
            diff_lane_cs INT,
            late_kills INT,
            late_deaths INT,
            late_assists INT,
            solo_kills INT,
            kill_participation INT,
            lane_cs INT,
            enemyjungleminionkills INT,
            vision_score INT,
            wards_placed INT,
            turret_damage INT,
            team_Dragon_kills INT,
            team_Horde_kills INT,
            team_riftHerald_kills INT,
            team_Baron_kills INT,
            team_ElderDragon_kills INT,
            team_Atakhan_kills INT,
            dragon_participation INT,
            dragon_deaths INT,
            elder_dragon_participation INT,
            elder_dragon_deaths INT,
            baron_nashor_participation INT,
            baron_nashor_deaths INT,
            riftherald_participation INT,
            riftherald_deaths INT,
            horde_participation INT,
            horde_deaths INT,
            atakhan_participation INT,
            atakhan_deaths INT,
            win INT,
            PRIMARY KEY (match_id, teamposition)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
    conn.commit()
    conn.close()
    print("✅ Match DB tables created in MySQL")

# %%
# create_champion_db_mysql.py
import mysql.connector
import json
import os

def create_champion_db():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    json_path = os.path.join(DATA_DIR, "champion.json")

    if not os.path.exists(json_path):
        print(f"❌ JSON 파일이 존재하지 않습니다: {json_path}")
        return
    mysql_config = {
        "host": "3.37.127.128",
        "user": "lol_local",
        "password": "!Jib990205", 
        "database": "champion_data",
        "port": 3306
    }

    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()
    # 테이블 생성
    cursor.execute("DROP TABLE IF EXISTS `champion`;")
    cursor.execute("""
    CREATE TABLE `champion` (
        champ_name VARCHAR(100),
        champ_name_KR VARCHAR(100),
        champ_tags VARCHAR(255),
        champ_key INT,
        PRIMARY KEY (champ_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    # JSON 로드
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    champions = data.get("data", {})

    # 데이터 삽입
    inserted = 0
    for champ in champions.values():
        champ_name_en = champ.get("id", "")
        champ_name_kr = champ.get("name", "")
        champ_tags = ",".join(champ.get("tags", []))
        champ_key = int(champ.get("key", 0))

        # MySQL에서는 ON DUPLICATE KEY UPDATE 사용
        cursor.execute("""
        INSERT INTO champion (champ_name, champ_name_KR, champ_tags, champ_key)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            champ_name=VALUES(champ_name),
            champ_name_KR=VALUES(champ_name_KR),
            champ_tags=VALUES(champ_tags)
        """, (champ_name_en, champ_name_kr, champ_tags, champ_key))
        inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ 챔피언 데이터를 MySQL DB에 저장했습니다. (총 {inserted}개)")



# %%migrate_sqlite_to_mysql_batch_fixed.py

# import sqlite3
# import mysql.connector
# import os

# # ------------------------------
# # 경로 설정
# # ------------------------------
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# DATA_DIR = os.path.join(BASE_DIR, "data")
# sqlite_db_path = os.path.join(DATA_DIR, "matchup_data.db")

# # ------------------------------
# # MySQL 서버 연결 설정
# # ------------------------------
# mysql_config = {
#     "host": "3.37.127.128",
#     "user": "lol_local",
#     "password": "!Jib990205", 
#     "database": "matchup_data",
#     "port": 3306
# }

# # ------------------------------
# # SQLite 연결
# # ------------------------------
# sqlite_conn = sqlite3.connect(sqlite_db_path)
# sqlite_cursor = sqlite_conn.cursor()

# # ------------------------------
# # MySQL 연결
# # ------------------------------
# mysql_conn = mysql.connector.connect(**mysql_config)
# mysql_cursor = mysql_conn.cursor()

# # ------------------------------
# # SQLite에 있는 모든 테이블 가져오기
# # ------------------------------
# sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
# tables = [row[0] for row in sqlite_cursor.fetchall()]

# for table in tables:
#     print(f"=== Migrating table: {table} ===")
    
#     # 1️⃣ 테이블 구조 가져오기
#     sqlite_cursor.execute(f"PRAGMA table_info({table})")
#     columns_info = sqlite_cursor.fetchall()  # (cid, name, type, notnull, dflt_value, pk)

#     # 2️⃣ MySQL용 CREATE TABLE 문 생성
#     col_defs = []
#     pk_columns = []
#     for col in columns_info:
#         name = col[1]
#         col_type = col[2].upper()
#         pk = col[5]

#         # INT이면 AUTO_INCREMENT 적용은 선택적으로
#         if "INT" in col_type:
#             mysql_type = "INT"
#         elif "TEXT" in col_type:
#             mysql_type = "VARCHAR(120)"
#         else:
#             mysql_type = col_type

#         col_defs.append(f"`{name}` {mysql_type}")

#         if pk > 0:  # 0보다 큰 값이면 복합 PK 포함
#             pk_columns.append(f"`{name}`")

#     pk_clause = f", PRIMARY KEY ({', '.join(pk_columns)})" if pk_columns else ""
#     create_sql = f"CREATE TABLE IF NOT EXISTS `{table}` ({', '.join(col_defs)}{pk_clause}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"

#     # 3️⃣ 테이블 생성
#     mysql_cursor.execute(f"DROP TABLE IF EXISTS `{table}`;")
#     mysql_cursor.execute(create_sql)

#     # 4️⃣ 데이터 옮기기 (배치 단위)
#     sqlite_cursor.execute(f"SELECT * FROM {table}")
#     rows = sqlite_cursor.fetchall()
#     if rows:
#         placeholders = ", ".join(["%s"] * len(columns_info))
#         # 중복 PK 발생 시 기존 값 업데이트
#         insert_sql = f"""
#         INSERT INTO `{table}` ({', '.join([col[1] for col in columns_info])})
#         VALUES ({placeholders})
#         ON DUPLICATE KEY UPDATE {', '.join([f"{col[1]}=VALUES({col[1]})" for col in columns_info])}
#         """

#         batch_size = 1000
#         for i in range(0, len(rows), batch_size):
#             batch_rows = rows[i:i+batch_size]
#             mysql_cursor.executemany(insert_sql, batch_rows)
#             mysql_conn.commit()

#     print(f"✅ {table}: {len(rows)} rows migrated in batches")

# # ------------------------------
# # 연결 종료
# # ------------------------------
# sqlite_conn.close()
# mysql_conn.close()
# print("🎉 Migration complete!")

# %%
