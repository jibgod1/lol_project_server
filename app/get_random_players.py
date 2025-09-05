# %%
import requests
import time
import random
import config

REGION = "kr"  # kr, na1, euw1 등
QUEUE = "RANKED_SOLO_5x5"
DIVISIONS = ['I', 'II', 'III', 'IV']  # 🔹 랜덤 선택용 division 리스트

def get_random_players(tier, max_players=1000):
    headers = {"X-Riot-Token": config.API_KEY}
    all_players = set()
    tried_pages = set()

    while len(all_players) < max_players:
        division = random.choice(DIVISIONS)  # 🔸 division을 매번 랜덤 선택
        random_page = random.randint(1, 20)

        if (division, random_page) in tried_pages:
            continue
        tried_pages.add((division, random_page))

        base_url = f"https://kr.api.riotgames.com/lol/league/v4/entries/{QUEUE}/{tier}/{division}"
        url = f"{base_url}?page={random_page}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            players = response.json()

            if len(players) < 50:
                continue

            for player in players:
                all_players.add(player["puuid"])
                if len(all_players) >= max_players:
                    break
        else:
            print(f"❌ 오류 발생! 상태 코드: {response.status_code}")
            break

        time.sleep(1.2)

    return list(all_players)


# %%



