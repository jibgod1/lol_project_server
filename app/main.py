from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json
import sqlite3
import os
import player_analysis
import get_player_puuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


app = FastAPI()

@app.get("/")
def root():
    return {"msg": "LOL Project API is running 🚀"}

@app.get("/analysis")
def root():
    puuid = get_player_puuid.get_player_puuid("정유영", "KR2")
    players = [{'riotId': '파 멸#혼란폭력', 'puuid': '0dK3NbFT-MTqNxGMMa5Bvf1wQ64LXkrjMCw_cd84oc5tCtScbfRrS9jKEdoqjj96F9f7nkPWCVwixQ', 'lane': 'TOP'}, 
            {'riotId': '이 드#kr0', 'puuid': '08eWvcrlhvPV9E3EY54D0OkUhPl8mdabGMLM0HYUqBtYxJdtOv8HYC3KD-8QFecJxeyBWPlSluWfUg', 'lane': 'JUNGLE'}, 
            {'riotId': '조맹맹맹맹#4545', 'puuid': 'RgA1dDKbM7SXFirQWWKwvidVtq5L6sH681UDXtruO5qDkEGRfki_brVP58yJrqKz-WJJD9PFguRhDA', 'lane': 'MIDDLE'}, 
            {'riotId': '비라악#KR1', 'puuid': 'c7Lan8kPys9fzR5RaKHXajv7ASYmqhdy31uZWEGgiISmwCyid2l6a06UeFjO6fzRPImsxyaxtNMy1g', 'lane': 'BOTTOM'}, 
            {'riotId': '안참는개#0217', 'puuid': '9abbI0eWCIYIconf8RHJsT4M2hDNwoktdOzvjrSWoh4EB7Yyt33XlgCzrG2gXm15r_Pb_Yy_7pGnug', 'lane': 'UTILITY'}, 
            {'riotId': '호떠기다#KR1', 'puuid': 'nDNgD_6Ocy9DRHVi_GbiCypOJA95hU4_T78y2I2hh0CX-kQ-k1fmaUNfMjjQZPjxJvtxdvOoiSYQzQ', 'lane': 'TOP'}, 
            {'riotId': '정유영#KR2', 'puuid': 'pgwqD1Btfiamr2RWra1w0GQ8cL9N0qyBusPfU1hjhGw8qDplNpn4ayWmCsiZeImmC9bwoar6gDTC2w', 'lane': 'JUNGLE'}, 
            {'riotId': '이 효 민#kr2', 'puuid': 'f93X58pGbdfPKEvn1UwPOcRFeGSguZLE4q0zzz4cpDl-qMhN6mof83qzZIs-Mc3xCGvxV74y9E8d4g', 'lane': 'MIDDLE'}, 
            {'riotId': '내똥매우커#박잉여', 'puuid': 'X1DvD3cwAamCre4nRNcTldQE2Q6MmOD8zbmjTiEzbIvMPsiGspoux8yTU--VinR7JlAGUy9CA4sgGQ', 'lane': 'BOTTOM'}, 
            {'riotId': '옆집누나의향기#KR1', 'puuid': 'PK5Xyk7tyfs2tuIF3wzUJmQQl6qxVslk0RYkuABA5_ux60tafETyNReCEeKUH5IVWyrx5EnnvTdGaQ', 'lane': 'UTILITY'}]
    players[0]["lane"] = "TOP"
    players[1]["lane"] = "BOTTOM"
    players[2]["lane"] = "MIDDLE"
    players[3]["lane"] = "UTILITY"
    players[4]["lane"] = "JUNGLE"
    players[5]["lane"] = "JUNGLE"
    players[6]["lane"] = "MIDDLE"
    players[7]["lane"] = "BOTTOM"
    players[8]["lane"] = "UTILITY"
    players[9]["lane"] = "TOP"
    for i, p in enumerate(players):
        if p["puuid"] == puuid:
            team = "blue" if i <= 4 else "red"
            break
    current_players = players.copy()

    blue_team = current_players[:5]
    red_team = current_players[5:]

    order = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

    blue_sorted = []
    for lane in order:
        for p in blue_team:
            if p["lane"] == lane:
                blue_sorted.append(p)
                break
                
    red_sorted = []
    for lane in order:
        for p in red_team:
            if p["lane"] == lane:
                red_sorted.append(p)
                break

    players = blue_sorted + red_sorted
    print(players)
    print(team)
    def generator():
        for comment in player_analysis.game_analysis(players, "MIDDLE", "BRONZE", team):
            yield json.dumps(comment) + "\n"

    return StreamingResponse(generator(), media_type="application/json")


