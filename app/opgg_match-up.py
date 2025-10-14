# opgg_winrate.py

import json
import requests
import time
import os
import sqlite3



def find_data_arrays(obj):
    results = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'data' and isinstance(value, list):
                results.append(value)
            results.extend(find_data_arrays(value))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(find_data_arrays(item))
    return results

def matchup(hero, position, tier, region, max_retries=3):
    
    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'no-cache',
        'next-router-state-tree': '%5B%22%22%2C%7B%22children%22%3A%5B%5B%22locale%22%2C%22en%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%22lol%22%2C%7B%22children%22%3A%5B%22champions%22%2C%7B%22children%22%3A%5B%5B%22champion%22%2C%22twistedfate%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%5B%22category%22%2C%22counters%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%5B%22position%22%2C%22mid%22%2C%22oc%22%5D%2C%7B%22children%22%3A%5B%22__PAGE__%3F%7B%5C%22tier%5C%22%3A%5C%22emerald_plus%5C%22%2C%5C%22target_champion%5C%22%3A%5C%22qiyana%5C%22%7D%22%2C%7B%7D%2C%22%2Flol%2Fchampions%2Ftwistedfate%2Fcounters%2Fmid%3Ftier%3Demerald_plus%26target_champion%3Dqiyana%22%2C%22refresh%22%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D',
        'next-url': '/en/lol/champions/twistedfate/counters/mid',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://op.gg/lol/champions/twistedfate/counters/mid?tier=emerald_plus&target_champion=qiyana',
        'rsc': '1',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    params = {
        'tier': tier,
        'region': region,
        '_rsc': '17eld',
    }

    url = f'https://op.gg/lol/champions/{hero}/counters/{position}'

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers)
            lines = resp.text.split('\n')

           
            parsed = None
            for idx in (-4, -5, -3, -2, -1):
                if len(lines) >= abs(idx):
                    frag = lines[idx][3:]
                    try:
                        parsed = json.loads(frag)
                        break
                    except:
                        continue

            if parsed is None:
                raise ValueError("响应解析失败（可能被限流或页面结构变化）")

            arrays = find_data_arrays(parsed)

            # 查找包含 win/play 字段的数据数组
            winrate_data = None
            for arr in arrays:
                if isinstance(arr, list) and arr and isinstance(arr[0], dict) and 'win' in arr[0] and 'champion' in arr[0]:
                    winrate_data = arr
                    break

            if not winrate_data:
                print(f'[건너뛰기] {hero}-{position}-{tier}-{region} no data')
                return None

            #filename = f'对位胜率_{hero}_{position}_{tier}_{region}.json'
            #with open(filename, 'w', encoding='utf-8') as f:
            #    json.dump(winrate_data, f, ensure_ascii=False, indent=4)
            #print(f'[✔] 已保存 {filename}')
            return winrate_data

        except Exception as e:
            if attempt < max_retries:
                print(f'[다시] {attempt}/{max_retries} 번 -> {hero}-{position}-{tier}-{region} : {e}')
                time.sleep(5 + attempt * 2)  # 逐次增加等待时间
            else:
                print(f'[실패] {hero}-{position}-{tier}-{region} -> {e}')
                return None

def ensure_db():
    conn = sqlite3.connect('matchup_data.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS matchup_winrate (
            hero TEXT,
            position TEXT,
            tier TEXT,
            region TEXT,
            opponent TEXT,
            win_rate REAL,
            win REAL,
            play REAL,
            PRIMARY KEY (hero, position, tier, region, opponent)
        )
    ''')
    conn.commit()
    conn.close()

def insert_winrate_to_db(hero, position, tier, region, winrate_data):
    conn = sqlite3.connect('matchup_data.db')
    cur = conn.cursor()
    try:
        for row in winrate_data:
            opponent_info = row.get('champion')
            opponent = opponent_info.get('key') if isinstance(opponent_info, dict) else opponent_info
            win_rate = row.get('win_rate')
            win = row.get('win')
            play = row.get('play')

            if not all([opponent,win_rate,win, play]):
                print(f'[⚠️NULL 데이터 건너뛰기] {hero}-{position}-{tier}-{region} -> {row}')
                continue

            cur.execute('''
                INSERT OR REPLACE INTO matchup_winrate 
                (hero, position, tier, region, opponent,win_rate,win, play)
                VALUES (?, ?, ?, ?, ?, ?, ?,?)
            ''', (
                str(hero),
                str(position),
                str(tier),
                str(region),
                str(opponent),
                float(win_rate),
                float(win),
                float(play)
            ))

        conn.commit()
        print(f'[✔] DataBase: {hero}-{position}-{tier}-{region}  {len(winrate_data)} 개')
    except Exception as e:
        print(f'[❌실패] {hero}-{position}-{tier}-{region} -> {e}')
    finally:
        conn.close()



if __name__ == '__main__':

  # ✅ 临时测试数据库写入是否成功
    ensure_db()
    #sample = [{'champion': 'garen', 'win': 52.3, 'play': 1000}]
    #insert_winrate_to_db('darius', 'top', 'iron', 'kr', sample)
    #print('[✅测试] 手动写入测试数据完毕')

    # 读取英雄 key
    with open('pickban数据.json', 'r', encoding='utf-8') as f:
        all_champions = json.load(f)
    hero_keys = [champ['key'] for champ in all_champions]

    positions = ['top', 'jungle', 'mid', 'bottom', 'support']
    tiers = ['iron','bronze', 'silver', 'gold', 'gold_plus', 'platinum',
             'platinum_plus', 'emerald', 'emerald_plus', 'diamond', 'diamond_plus']
    regions = ['kr']  

    total = len(hero_keys) * len(positions) * len(tiers) * len(regions)
    count = 0

    for hero in hero_keys:
        for position in positions:
            for tier in tiers:
                for region in regions:
                    try:
                        result = matchup(hero, position, tier, region)
                        if result:
                            insert_winrate_to_db(hero, position, tier, region, result)
                            count += 1
                    except Exception as e:
                        print(f'[false] {hero}-{position}-{tier}-{region} -> {e}')
                    time.sleep(1.0)  # 限流保护

    print(f'[✔] 완료, 총：{count}/{total}')
