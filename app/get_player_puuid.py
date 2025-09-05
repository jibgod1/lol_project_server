# %%
import requests
from urllib.parse import quote
import config 

#유저 이름으로 puuid가져오기
def get_player_puuid(summoner_name, tag):
    api_key=config.API_KEY
    #name encoding
    encodedName = quote(summoner_name)
    #url
    summoner_url =f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encodedName}/{tag}"
    #api key
    headers = {
    "X-Riot-Token": api_key
    }
    # api call
    response = requests.get(summoner_url, headers=headers)
    player_id=requests.get(summoner_url, headers=headers).json()

    if response.status_code == 200:
        puuid=player_id['puuid']
        print("get_player_puuid:", puuid)
        return puuid
    else:
        print(f"API 요청 실패: {response.status_code}")
        return response.status_code


# %%



