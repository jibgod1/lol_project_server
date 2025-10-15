# %%
import json
import os
import time
import config
import get_player_puuid
import get_match_id
import get_random_players
import game_info
from create_db import create_match_db

create_match_db()

tier1 = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND"]
#tier2 = ["PLATINUM", "EMERALD", "DIAMOND"]
player_count = 300
players_per_batch = 10 # 몇명씩 잘라서 수집할지
matches_per_player = 10  # 각 플레이어 당 수집할 매치 수
positions = ['TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY']

start_time = time.time()

# 1. 플레이어 수집
for tier in tier1:
    players = get_random_players.get_random_players(tier, player_count)
    print(f"총 {len(players)}명의 플레이어 데이터를 가져왔습니다.")
    
    # 2. 플레이어를 10명씩 나누어 처리
    for i in range(0, len(players), players_per_batch):
        batch_players = players[i:i + players_per_batch]
    
        print(f"\n🔹 {i+1} ~ {i+len(batch_players)}번 플레이어 매치 수집 중...")
    
        # 매치 ID 수집
        match_ids = get_match_id.get_matches_for_players(batch_players, matches_per_player)
    
    
        print(f"▶ 처리할 매치 수: {len(match_ids)}")
    
        flag="EVEN"
    
        # 각 매치에 대해 데이터 수집
        for match in match_ids:
            try:
                match_data = game_info.game_info(match, tier, flag)
                if flag =="EVEN":
                    flag="ODD"
            except Exception as e:
                print(f"❌ {match} 처리 중 에러: {e}")
                continue
    
        time.sleep(1.2)  # API 과부하 방지
    
    print(f"{tier} 수집 종료")

# 종료 시간 및 총 소요시간 출력
end_time = time.time()
elapsed = end_time - start_time

# 시:분:초 단위로 변환해서 출력
hours = int(elapsed // 3600)
minutes = int((elapsed % 3600) // 60)
seconds = int(elapsed % 60)
print(f"\n✅ 전체 수집 완료! 총 소요 시간: {hours}시간 {minutes}분 {seconds}초")

# %%



