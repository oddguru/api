from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from supabase import create_client
from pydantic import BaseModel
import datetime
import requests
import os
import logging
from typing import List, Dict

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="OddGuru PRO v11.0 - 2025 + IA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === SUPABASE ===
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# === MODELOS ===
class BetIn(BaseModel):
    match: str
    home_team: str
    away_team: str
    market: str
    selection: str
    odd: float
    edge: float
    why: str

class BetResult(BaseModel):
    match: str
    market: str
    selection: str
    result: str

# === ENDPOINTS BÁSICOS ===
@app.post("/api/add-bet")
def add_bet(bet: BetIn):
    data = bet.dict()
    data["bet_date"] = datetime.datetime.utcnow().isoformat()
    supabase.table("bets").delete()\
        .eq("match", bet.match)\
        .eq("market", bet.market)\
        .execute()
    supabase.table("bets").insert(data).execute()
    return {"status": "ok"}

@app.post("/api/record-result")
def record_result(res: BetResult):
    supabase.table("bets").update({"result": res.result})\
        .eq("match", res.match)\
        .eq("market", res.market)\
        .execute()
    return {"status": "ok"}

@app.get("/api/active-bets")
def active_bets():
    data = supabase.table("bets")\
        .select("*")\
        .is_("result", "null")\
        .order("bet_date", desc=True)\
        .execute()
    return {"active_bets": data.data}

@app.get("/api/history")
def history():
    data = supabase.table("bets").select("*")\
        .not_.is_("result", "null")\
        .order("created_at", desc=True)\
        .execute()
    bets = data.data
    total = len(bets)
    wins = len([b for b in bets if b["result"] == "win"])
    profit = sum((b["odd"] - 1) * 100 for b in bets if b["result"] == "win") - (total - wins) * 100
    roi = (profit / (total * 100) * 100) if total > 0 else 0
    return {
        "total_bets": total,
        "wins": wins,
        "losses": total - wins,
        "profit": round(profit, 2),
        "roi": f"{roi:.1f}%" if total > 0 else "0.0%",
        "history": bets[:50]
    }

# === API-SPORTS v3 (PRO) ===
API_KEY = os.getenv("API_SPORTS_KEY")
HEADERS = {
    "x-apisports-key": API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}
BASE_URL = "https://v3.football.api-sports.io"

# === BUSCAR JOGOS DO DIA (BRASILEIRÃO) ===
def get_today_fixtures() -> List[Dict]:
    today = datetime.date.today().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/fixtures"
    params = {"league": 71, "season": 2025, "date": today}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code != 200:
            logger.error(f"Fixtures error: {resp.status_code}")
            return []
        return resp.json().get("response", [])
    except Exception as e:
        logger.error(f"Fixtures exception: {e}")
        return []

# === STATS DO TIME ===
def get_team_stats(team_id: int) -> Dict:
    url = f"{BASE_URL}/teams/statistics"
    params = {"team": team_id, "league": 71, "season": 2025}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code != 200:
            return {}
        data = resp.json().get("response", {})
        if not data: return {}
        s = data.get("statistics", [{}])[0]
        return {
            "jogos": s.get("fixtures", {}).get("played", {}).get("total", 0),
            "vitorias": s.get("fixtures", {}).get("wins", {}).get("total", 0),
            "gols_marcados": s.get("goals", {}).get("for", {}).get("total", {}).get("total", 0),
            "gols_sofridos": s.get("goals", {}).get("against", {}).get("total", {}).get("total", 0),
            "clean_sheets": s.get("clean_sheet", {}).get("total", 0),
            "cartoes": s.get("cards", {}).get("yellow", {}).get("total", 0)
        }
    except: return {}

# === H2H ===
def get_h2h(team1: int, team2: int) -> List[Dict]:
    url = f"{BASE_URL}/fixtures/head2head"
    params = {"h2h": f"{team1}-{team2}"}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        return resp.json().get("response", [])
    except: return []

# === GERAR VALUE BETS (IA) ===
def generate_value_bets():
    fixtures = get_today_fixtures()
    if not fixtures:
        return {"status": "sem jogos hoje"}

    added = 0
    for fixture in fixtures[:5]:  # 5 jogos por dia
        home = fixture["teams"]["home"]["name"]
        away = fixture["teams"]["away"]["name"]
        match = f"{home} vs {away}"
        home_id = fixture["teams"]["home"]["id"]
        away_id = fixture["teams"]["away"]["id"]

        home_stats = get_team_stats(home_id)
        away_stats = get_team_stats(away_id)
        h2h = get_h2h(home_id, away_id)

        # Over 2.5
        total_goals = (home_stats.get("gols_marcados", 0) + away_stats.get("gols_sofridos", 0)) / max(home_stats.get("jogos", 1), 1)
        if total_goals > 2.7:
            bet = {
                "match": match,
                "home_team": home,
                "away_team": away,
                "market": "gols",
                "selection": "Over 2.5",
                "odd": 1.90,
                "edge": 0.25,
                "why": f"Média {total_goals:.1f} gols/jogo. {len([h for h in h2h if h['goals']['home'] + h['goals']['away'] > 2])}/10 H2H Over 2.5"
            }
            add_bet_to_db(bet)
            added += 1

        # Ambos Marcam
        btts_count = len([h for h in h2h if h['goals']['home'] > 0 and h['goals']['away'] > 0])
        if btts_count >= 6:
            bet = {
                "match": match,
                "home_team": home,
                "away_team": away,
                "market": "ambos marcam",
                "selection": "Sim",
                "odd": 1.85,
                "edge": 0.22,
                "why": f"BTTS em {btts_count}/10 H2H. {home}: {home_stats.get('gols_marcados',0)} gols, {away}: {away_stats.get('gols_marcados',0)} gols"
            }
            add_bet_to_db(bet)
            added += 1

    return {"status": f"{added} value bets geradas para hoje!"}

def add_bet_to_db(bet: Dict):
    data = {**bet, "bet_date": datetime.datetime.utcnow().isoformat()}
    supabase.table("bets").delete().eq("match", bet["match"]).eq("market", bet["market"]).execute()
    supabase.table("bets").insert(data).execute()

# === ENDPOINTS NOVOS ===
@app.get("/api/generate-today")
def generate_today():
    return generate_value_bets()

@app.get("/api/clear-bets")
def clear_bets():
    supabase.table("bets").delete().execute()
    return {"status": "bets limpas"}

# === SERVIR FRONTEND ===
app.mount("/", StaticFiles(directory="public", html=True), name="static")
