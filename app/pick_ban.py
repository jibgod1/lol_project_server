import json
import requests
import sqlite3
import argparse
import sqlite3
import time
from typing import List, Dict, Any

DEFAULT_REGIONS = ["kr"] 
def pickban(tier='gold',region='kr'):
    
    cookies = {
        '_otm': 'true',
        '_gcl_au': '1.1.1781006264.1755868328',
        '_ga': 'GA1.1.725680204.1755868328',
        '_olvt': 'false',
        '_lr_env_src_ats': 'false',
        'usprivacy': '1---',
        'sharedid': '421d38dd-abef-4e1a-82b6-8734932702b2',
        '_lr_sampling_rate': '100',
        '_pubcid': 'fc557adf-6287-4b5f-bd2e-0ff66f1d05c9',
        '_ol': 'en_US',
        'FCNEC': '%5B%5B%22AKsRol_MOuJeSA28pugTjb7gsIC0-PQcijOcyZaXJPK4EIybAKDvyvTHCPnvml3wuLOI98qZjCT4lr3XcqpJL7aH7kWcF7YZUJ7m4EEA_PU0F-EKfFHCPoyvXKe3A_eiVbZzjhsR4VUC38NeYDHRBvTPkST33im_1A%3D%3D%22%5D%5D',
        'sharedid_cst': '3CwgLLcsIA%3D%3D',
        '_lr_retry_request': 'true',
        'pbjs-unifiedid_cst': 'zix7LPQsHA%3D%3D',
        '__gads': 'ID=fa00725be5f599e6:T=1756099187:RT=1756107971:S=ALNI_MbSmsbGNMRKRx6kZrGCkLFTeNmndw',
        '__gpi': 'UID=00001185c1108e90:T=1756099187:RT=1756107971:S=ALNI_MaHpA5MNs1KRVplU3fM1NR2IMqCEQ',
        '__eoi': 'ID=498d4db754b7ea90:T=1756099187:RT=1756107971:S=AA-AfjaEd4dHqnfbRx7jt7KzxcyB',
        '_opvc': '13',
        '_awl': '2.1756108008.5-60658fbe81b0d58a3c8d2118f340dc12-6763652d617369612d6561737431-0',
        'pbjs-unifiedid': '%7B%22TDID%22%3A%22f0e8584c-c1c1-49c0-a993-d242bd8ee89c%22%2C%22TDID_LOOKUP%22%3A%22TRUE%22%2C%22TDID_CREATED_AT%22%3A%222025-07-25T07%3A46%3A49%22%7D',
        'cto_bidid': 'b01MUF9nckNuNlZMRk1qRDVVR3Myd21OQ2QxeWd5V3poRUV2OXB1cnc2NmNNM1padjc5MEZKJTJCenpwY3BlQUVpbHNUU3lyWmdETTB3VXlHbWRtblBlTXc1NjFRMGVHSzFZSUhzZHIlMkY0SWt6Znc2TXMlM0Q',
        '__binsSID': 'be97c92c-3cb1-4417-9eb8-59aef6db0988',
        '_ga_HKZFKE5JEL': 'GS2.1.s1756107945$o4$g1$t1756108028$j38$l0$h0',
        '_ga_HG9DB5ECL8': 'GS2.1.s1756107946$o4$g1$t1756108028$j38$l0$h1882999296',
        '_ga_WCXGQGETWH': 'GS2.1.s1756107946$o4$g1$t1756108028$j39$l0$h7089076',
        '_ga_37HQ1LKWBE': 'GS2.1.s1756107946$o4$g1$t1756108028$j39$l0$h0',
        '_pubcid_cst': '3CwgLLcsIA%3D%3D',
        'cto_bundle': 'V-Ydf19oRWlncUFpNkZXRzZZTFJRSGVmRGNpb1BaaSUyRkNISnlxSXlNN0pNbiUyQjdKQ1JpUEpSUnNVbEx4Sk92TWZJZDMwV0R4ZjQwWSUyQmFWTm5PMmx2THR0M2R2ZTJob2tlc2JPbjFQUXRlbjlaVDNTRUF2dGMxa25NUGFnUHMlMkJmaEs3TU5mdFVMSHhLY2xZejRFQkhGaHJHTFFQUlRhcmZJcEx2UVJiNVZMWEYwY2JtUkFDSW83djlXNFF6YXJEZ1hzUTBFUXUlMkY2VllQNmVEdkpQJTJGT0xOM2RKdnF3JTNEJTNE',
        '_dd_s': 'rum=0&expire=1756108957625',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'no-cache',
        'next-router-state-tree': '%5B%22%22%2C%7B%22children%22%3A%5B%5B%22locale%22%2C%22en%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%22lol%22%2C%7B%22children%22%3A%5B%22champions%22%2C%7B%22children%22%3A%5B%22__PAGE__%3F%7B%5C%22position%5C%22%3A%5C%22top%5C%22%7D%22%2C%7B%7D%2C%22%2Flol%2Fchampions%3Fposition%3Dtop%22%2C%22refresh%22%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D',
        'next-url': '/en/lol/champions',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://op.gg/lol/champions?position=top',
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
        'position': 'all',
         'region': region,
         'tier': tier,
        '_rsc': 'f2ql4',
    }

    url = 'https://op.gg/lol/champions'
    response = requests.get(url, params=params, cookies=cookies, headers=headers)
    lines = response.text.split('\n')

    # 尝试找包含 data 的 JSON
    parsed = None
    for idx in range(-8, 0):
        if abs(idx) <= len(lines):
            try:
                candidate = json.loads(lines[idx][3:])
                if isinstance(candidate, list) and isinstance(candidate[-1], dict) and 'data' in candidate[-1]:
                    parsed = candidate[-1]['data']
                    break
            except:
                continue

    if not parsed:
        print(f'[❌실패] {tier}-{region} Not found data  JSON')
        return

    data = parsed

    # 删除 positionCounters 字段
    for champ in data:
        champ.pop('positionCounters', None)

    # 写入数据库
    conn = sqlite3.connect('pick_ban_data.db')
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS pick_ban_data (
            key TEXT,
            name TEXT,
            positionName TEXT,
            tier TEXT,
            region TEXT,
            positionWinRate REAL,
            positionPickRate REAL,
            positionBanRate REAL,
            positionRoleRate REAL,
            image_url TEXT,
            PRIMARY KEY (key, positionName, tier, region)
        )
    ''')

    for champ in data:
        cur.execute('''
            INSERT INTO pick_ban_data (
                key, name, positionName, tier, region,
                positionWinRate, positionPickRate, positionBanRate,
                positionRoleRate, image_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key, positionName, tier, region) DO UPDATE SET
                name=excluded.name,
                positionWinRate=excluded.positionWinRate,
                positionPickRate=excluded.positionPickRate,
                positionBanRate=excluded.positionBanRate,
                positionRoleRate=excluded.positionRoleRate,
                image_url=excluded.image_url
        ''', (
            champ['key'],
            champ['name'],
            champ.get('positionName'),
            tier,
            region,
            champ.get('positionWinRate'),
            champ.get('positionPickRate'),
            champ.get('positionBanRate'),
            champ.get('positionRoleRate'),
            champ.get('image_url')
        ))

    conn.commit()
    conn.close()
    print(f'[✔] : {tier}-{region}  {len(data)} ')


if __name__ == '__main__':
    tiers = ['iron','bronze','silver','gold','gold_plus','platinum',
             'platinum_plus','emerald','emerald_plus','diamond','diamond_plus']
    regions = ['kr']

    total = len(tiers) * len(regions)
    count = 0

    for tier in tiers:
        for region in regions:
            try:
                pickban(tier, region)
                count += 1
            except Exception as e:
                print(f'[❌fals] {tier}-{region} -> {e}')
            time.sleep(2)

    print(f'[✔] 완료 {count}/{total}')