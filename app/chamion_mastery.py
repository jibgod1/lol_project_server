# %%
import requests
import json
import os
import sqlite3

import importnb
with importnb.Notebook():  # Notebook 환경을 활성화
    import config
    import get_player_puuid  


def get_champion_mastery(summoner_name, tag):
    puuid = get_player_puuid.get_player_puuid(summoner_name, tag)
    api_key = config.API_KEY
    headers = {"X-Riot-Token": api_key}
    mastery_url = f"https://kr.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
    
    # 숙련도 API 요청
    mastery_res = requests.get(mastery_url, headers=headers)
    if mastery_res.status_code != 200:
        print(f"API 요청 실패: {mastery_res.status_code}")
        return mastery_res.status_code
    mastery_data = mastery_res.json()

    conn = sqlite3.connect("champion_data.db")
    cursor = conn.cursor()

    # 챔피언 키 기준으로 이름들 매핑
    result = []

    for entry in mastery_data:
        champ_key = entry.get("championId")
        champ_level = entry.get("championLevel")

        cursor.execute("SELECT champ_name, champ_name_KR FROM champion WHERE champ_key = ?", (champ_key,))
        row = cursor.fetchone()

        if row:
            champ_name_en, champ_name_kr = row
            result.append({
                "champion_key": champ_key,
                "champion_name_en": champ_name_en,
                "champion_name_kr": champ_name_kr,
                "champion_level": champ_level
            })

    conn.close()

     # 📁 data 폴더가 없다면 생성
    os.makedirs("data", exist_ok=True)

    # 저장 경로 설정
    file_name = f"{summoner_name}_{tag}_mastery.json"
    save_path = os.path.join("data", file_name)

    # JSON 파일 저장
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    print(f"숙련도 데이터가 '{save_path}'에 저장되었습니다.")
    


# %%
get_champion_mastery("monrin", "KR1")

# %%



