# %%
import time
import requests
import config

def get_matches_for_players(players, match_count):
    base_url = "https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{}/ids?type=ranked&count={}"
    headers = {"X-Riot-Token": config.API_KEY}

    all_matches = []

    for puuid in players:
        while True:  # 재시도 루프
            url = base_url.format(puuid, match_count)
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                all_matches.extend(response.json())
                break  # 성공했으니 루프 탈출

            elif response.status_code == 429:
                print("⏳ 429 오류 발생! 10초 후 다시 시도합니다...")
                time.sleep(10)  # 🔹 10초 대기 후 다시 시도

            else:
                print(f"❌ {puuid}의 매치 데이터를 가져오는 중 오류 발생! 상태 코드: {response.status_code}")
                break  # 기타 오류는 재시도하지 않음

        time.sleep(0.5)  # API 호출 간 시간 간격 유지 (권장)

    return all_matches


# %%



