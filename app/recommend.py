import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math
import json
import mysql.connector
from config import PASSWARD


# ✅ MySQL 설정
mysql_pick_ban_config = {
    "host": "3.37.127.128",
    "user": "lol_local",
    "password": PASSWARD,
    "database": "pick_ban_data",
    "port": 3306
}
mysql_matchup_config = {
    "host": "3.37.127.128",
    "user": "lol_local",
    "password": PASSWARD,
    "database": "matchup_data",
    "port": 3306
}
DEFAULT_WEIGHTS = {
    "mastery": 0.5,
    "win_rate": 0.35,
    "pick_rate": 0.15,
}

TOP_N_PICKS = 3
TOP_N_BANS_PER_PICK = 3
TOP_N_META_BANS = 2


@dataclass
class UserInfo:
    tier: str
    position: str
    champion_mastery: Dict[str, int]


# ✅ DB 연결 함수
def _open_db(config: dict):
    try:
        conn = mysql.connector.connect(**config)
        return conn
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return None


# ✅ Meta Stats (챔피언 메타 정보)
def _fetch_meta_stats(hero: str, position: str, tier: str, conn) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if conn is None:
        return (None, None, None)

    sql = """
        SELECT positionWinRate, positionPickRate, positionBanRate
          FROM pick_ban_data
         WHERE LOWER(champ_key)=%s AND LOWER(positionName)=%s AND LOWER(tier)=%s
         LIMIT 1
    """
    cur = conn.cursor()
    cur.execute(sql, (hero.lower(), position.lower(), tier.lower()))
    row = cur.fetchone()
    cur.close()
    if not row:
        return (None, None, None)

    wr, pr, br = row
    return float(wr), float(pr), float(br)


# ✅ Meta 밴 데이터 가져오기
def fetch_meta_top_bans(position: str, tier: str, conn, top_k: int = 5) -> List[str]:
    if conn is None:
        return []

    sql = """
        SELECT champ_key, positionBanRate
          FROM pick_ban_data
         WHERE LOWER(positionName)=%s AND LOWER(tier)=%s
         ORDER BY positionBanRate DESC
         LIMIT %s
    """
    cur = conn.cursor()
    cur.execute(sql, (position.lower(), tier.lower(), top_k))
    rows = cur.fetchall()
    cur.close()
    return [r[0].lower() for r in rows]


# ✅ 매치업 카운터 데이터
def fetch_counters(hero: str, position: str, tier: str, conn, top_k: int = 3) -> List[str]:
    if conn is None:
        return []

    sql = """
        SELECT opponent, win_rate
          FROM matchup_winrate
         WHERE LOWER(hero)=%s AND LOWER(position)=%s AND LOWER(tier)=%s
         ORDER BY win_rate ASC
         LIMIT %s
    """
    cur = conn.cursor()
    cur.execute(sql, (hero.lower(), position.lower(), tier.lower(), top_k))
    rows = cur.fetchall()
    cur.close()
    return [r[0].lower() for r in rows]

# Score Calculation
def _norm_pct(v: Optional[float], base: float = 50.0, scale: float = 15.0) -> float:
    if v is None:
        return 0.0
    v = max(0.0, min(100.0, float(v)))
    return max(-1.0, min(1.0, (v - base) / scale))


def _norm_pick_rate(pr: Optional[float]) -> float:
    if pr is None or pr <= 0:
        return 0.0
    x = pr / 100.0
    return math.log1p(9 * x) / math.log1p(9)


def compute_pick_score(hero: str, mastery: int, position: str, tier: str,
                       meta_conn: Optional[sqlite3.Connection],
                       weights: Dict[str, float] = DEFAULT_WEIGHTS,
                       max_mastery: int = 11) -> Tuple[float, Dict[str, float], Dict[str, Optional[float]]]:
    wr = pr = br = None
    if meta_conn:
        wr, pr, br = _fetch_meta_stats(hero, position, tier, meta_conn)

    comp = {
        "mastery": max(0.0, min(1.0, mastery / float(max_mastery))),
        "win_rate": (_norm_pct(wr) + 1.0) / 2.0,
        "pick_rate": _norm_pick_rate(pr),
    }
    score = (weights.get("mastery", 0)*comp["mastery"]
           + weights.get("win_rate", 0)*comp["win_rate"]
           + weights.get("pick_rate", 0)*comp["pick_rate"])
    raw = {"wr": wr, "pr": pr, "br": br}
    return score, comp, raw


#  Recommendation 
def recommend_picks(user: UserInfo,
                    meta_conn: Optional[sqlite3.Connection],
                    top_n: int = TOP_N_PICKS):
    items = []
    for hero, m in user.champion_mastery.items():
        # 检查该英雄在该位置是否有数据
        wr, pr, br = _fetch_meta_stats(hero, user.position, user.tier, meta_conn)
        if wr is None and pr is None: 
            continue

        s, comp, raw = compute_pick_score(hero, m, user.position, user.tier, meta_conn)
        items.append((hero, s, comp, raw, m))

    items.sort(key=lambda t: t[1], reverse=True)
    return items[:top_n]



def recommend_bans_for_pick(hero: str, user: UserInfo,
                            matchup_conn: Optional[sqlite3.Connection],
                            meta_conn: Optional[sqlite3.Connection],
                            k_counters: int = TOP_N_BANS_PER_PICK,
                            k_meta: int = TOP_N_META_BANS) -> Dict[str, List[str]]:
    counters = fetch_counters(hero, user.position, user.tier, matchup_conn)[:k_counters]
    meta_bans = fetch_meta_top_bans(user.position, user.tier, meta_conn, top_k=max(k_meta, 0))

    seen = set()
    ordered = []
    for name in counters + meta_bans:
        n = name.lower()
        if n not in seen and n != hero.lower():
            seen.add(n)
            ordered.append(n)

    return {
        "counters": [c.lower() for c in counters],
        "meta": [m.lower() for m in meta_bans],
        "final": ordered[:max(k_counters + k_meta, 1)]
    }





def run(user: UserInfo,
        top_n_picks: int = TOP_N_PICKS) -> Dict:
    meta_conn = _open_db(mysql_pick_ban_config)
    matchup_conn = _open_db(mysql_matchup_config)

    print(f"meta_conn: {meta_conn}")
    print(f"matchup_conn: {matchup_conn}")

    try:
        picks = recommend_picks(user, meta_conn, top_n=top_n_picks)
        results = []
        for hero, score, comp, raw, mastery in picks:
            bans = recommend_bans_for_pick(hero, user, matchup_conn, meta_conn)
            results.append({
                "hero": hero,
                "score": round(score, 4),
                "components": {k: round(v, 4) for k, v in comp.items()},
                "raw_meta": raw,
                "mastery": mastery,
                "bans": bans
            })
        return {
            "user": {
                "tier": user.tier,
                "position": user.position,
                "champion_mastery": user.champion_mastery
            },
            "picks": results
        }
    finally:
        if meta_conn: meta_conn.close()
        if matchup_conn: matchup_conn.close()


#  Print
def _pct(v: Optional[float]) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v):.1f}%"
    except Exception:
        return "-"


def _rat(v: Optional[float]) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v):.2f}"
    except Exception:
        return "-"


def pretty_print(result: Dict):
    user = result.get("user", {})
    picks = result.get("picks", [])

    print(f" 티어     : {user.get('tier', '-')}\n 포지션   : {user.get('position', '-')}\n")
    print(" 보유 숙련도 요약:")
    cm = user.get("champion_mastery", {})
    if cm:
        sorted_cm = sorted(cm.items(), key=lambda x: x[1], reverse=True)
        top_line = ", ".join([f"{k.title()} {v}" for k, v in sorted_cm[:6]])
        print(f"  - 상위 숙련도: {top_line}{' ...' if len(sorted_cm) > 6 else ''}\n")
    else:
        print("  - (숙련도 데이터 없음)\n")

    if not picks:
        print(" 추천 결과 없음")
        return

    print("| No | 챔피언         | 종합점수 | 숙련도 | 승률  | 픽률  |")

    for i, item in enumerate(picks, 1):
        hero = item.get("hero", "-").title()
        score = _rat(item.get("score", 0.0))
        mastery = f"{int(item.get('mastery', 0))}"
        wr = _pct(item.get("raw_meta", {}).get("wr"))
        pr = _pct(item.get("raw_meta", {}).get("pr"))
        print(f"| {i:<2} | {hero:<13} | {score:>7} | {mastery:>5} | {wr:>5} | {pr:>5} |")

    for i, item in enumerate(picks, 1):
        hero = item.get("hero", "-").title()
        bans = item.get("bans", {})
        counters = bans.get("counters", [])
        meta = bans.get("meta", [])
        final = bans.get("final", [])

        print(f"[{i}] 픽: {hero}")
        print(f"  - 카운터 밴: {', '.join([x.title() for x in counters]) if counters else '-'}")
        print(f"  - 메타 밴  : {', '.join([x.title() for x in meta]) if meta else '-'}")
        print(f"  => 최종 밴 : {', '.join([x.title() for x in final]) if final else '-'}\n")




if __name__ == "__main__":
    print("=== 추천 Pick & Ban 시스템 ===\n")

    try:
        tier = input("당신의 티어를 입력하세요 : ").strip().lower()
        position = input("플레이할 포지션을 입력하세요 : ").strip().lower()
    except Exception as e:
        print("입력 오류:", e)
        raise SystemExit(1)

    champion_mastery = {}
    try:
        with open("monrin_KR1_mastery.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            champion_mastery = {entry["champion_name_en"].lower(): entry["champion_level"] for entry in data}

        if not champion_mastery:
            print("숙련도 데이터가 없습니다.")
            raise SystemExit(1)

    except Exception as e:
        print("monrin_KR1_mastery.json 로딩 실패:", e)
        raise SystemExit(1)

    userinfo = UserInfo(
        tier=tier,
        position=position,
        champion_mastery=champion_mastery
    )

    res = run(userinfo)
    pretty_print(res)


