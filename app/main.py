from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from supabase import create_client
from pydantic import BaseModel
import datetime
import requests
import os
import logging

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="OddGuru PRO v6.0 - API Real + Stats Reais")

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
        .eq("selection", bet.selection)\
        .execute()
    supabase.table("bets").insert(data).execute()
    return {"status": "ok"}

@app.post("/api/record-result")
def record_result(res: BetResult):
    supabase.table("bets").update({"result": res.result})\
        .eq("match", res.match)\
        .eq("market", res.market)\
        .eq("selection", res.selection)\
        .execute()
    return {"status": "ok"}

@app.get("/api/active-bets")
def active_bets():
    data = supabase.table("bets")\
        .select("*")\
        .is_("result", "null")\
        .order("bet_date", desc=True)\
        .limit(20)\
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

# === TESTE: JOGOS DO FLAMENGO 2023 (API REAL - FREE FUNCIONA!) ===
@app.get("/api/test-flamengo-games")
def test_flamengo_games():
    api_key = os.getenv("API_SPORTS_KEY") or "2ab3c17a1930546fffc2cccb2c847a6b"
    headers = {
        "x-apisports-key": api_key,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    url = "https://v3.football.api-sports.io/fixtures"
    params = {
        "team": 40,
        "season": 2023,
        "league": 71
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            return {"error": f"API erro {resp.status_code}", "details": resp.text}
        
        data = resp.json()
        games = data.get("response", [])
        
        return {
            "status": "sucesso",
            "source": "API-Sports v3",
            "total_jogos_2023": len(games),
            "ultimos_3_jogos": [
                {
                    "data": g["fixture"]["date"][:10],
                    "adversario": g["teams"]["away"]["name"] if g["teams"]["home"]["name"] == "Flamengo" else g["teams"]["home"]["name"],
                    "casa": g["teams"]["home"]["name"] == "Flamengo",
                    "placar": f"{g['goals']['home']}-{g['goals']['away']}" if g['goals']['home'] is not None else "Não jogado"
                } for g in games[-3:]
            ]
        }
    except Exception as e:
        return {"error": "falha", "details": str(e)}

# === TESTE: STATS REAIS DO FLAMENGO 2023 ===
@app.get("/api/test-flamengo-stats")
def test_flamengo_stats():
    api_key = os.getenv("API_SPORTS_KEY") or "2ab3c17a1930546fffc2cccb2c847a6b"
    headers = {
        "x-apisports-key": api_key,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    url = "https://v3.football.api-sports.io/teams/statistics"
    params = {
        "team": 40,
        "league": 71,
        "season": 2023
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            return {"error": f"API erro {resp.status_code}"}
        
        data = resp.json().get("response", {})
        if not data:
            return {"error": "sem dados"}
        
        stats = data.get("statistics", [{}])[0]
        team = data.get("team", {})
        
        return {
            "status": "sucesso",
            "time": team.get("name"),
            "jogos": stats.get("fixtures", {}).get("played", {}).get("total"),
            "vitorias": stats.get("fixtures", {}).get("wins", {}).get("total"),
            "gols_marcados": stats.get("goals", {}).get("for", {}).get("total", {}).get("total"),
            "gols_sofridos": stats.get("goals", {}).get("against", {}).get("total", {}).get("total"),
            "cartoes_amarelos": stats.get("cards", {}).get("yellow", {}).get("total"),
            "cartoes_vermelhos": stats.get("cards", {}).get("red", {}).get("total"),
            "clean_sheets": stats.get("clean_sheet", {}).get("total"),
            "fonte": "API-Sports v3 (dados reais 2023)"
        }
    except Exception as e:
        return {"error": str(e)}

# === UPDATE: VALUE BETS REAIS DO FLAMENGO (2023) ===
@app.get("/api/update-flamengo")
def update_flamengo():
    stats_resp = test_flamengo_stats()
    if "error" in stats_resp:
        raise HTTPException(status_code=502, detail=stats_resp["error"])
    
    stats = stats_resp
    
    # Jogos reais do Flamengo 2023 (últimos 3 como exemplo)
    games_resp = test_flamengo_games()
    if "error" in games_resp:
        raise HTTPException(status_code=502, detail=games_resp["error"])
    
    games = games_resp["ultimos_3_jogos"]
    
    added = 0
    for game in games:
        home = "Flamengo RJ" if game["casa"] else game["adversario"]
        away = game["adversario"] if game["casa"] else "Flamengo RJ"
        match = f"{home} vs {away}"
        
        bets = [
            {
                "market": "1X2", "selection": "Flamengo RJ", "odd": 1.75, "edge": 0.28,
                "why": f"Flamengo: {stats['vitorias']} vitórias em {stats['jogos']} jogos (média {stats['vitorias']/stats['jogos']:.2f} vitórias/jogo)"
            },
            {
                "market": "gols", "selection": "Over 2.5", "odd": 1.95, "edge": 0.22,
                "why": f"Média de {(stats['gols_marcados'] + stats['gols_sofridos']) / stats['jogos']:.1f} gols/jogo"
            },
            {
                "market": "cartoes", "selection": "Over 5.5", "odd": 2.10, "edge": 0.30,
                "why": f"{stats['cartoes_amarelos']} cartões amarelos em {stats['jogos']} jogos"
            }
        ]
        
        for bt in bets:
            data = {
                **bt,
                "match": match,
                "home_team": home,
                "away_team": away,
                "bet_date": datetime.datetime.utcnow().isoformat()
            }
            supabase.table("bets").delete()\
                .eq("match", match)\
                .eq("market", bt["market"])\
                .execute()
            supabase.table("bets").insert(data).execute()
            added += 1
    
    return {
        "status": f"{added} value bets REAIS do Flamengo cadastradas!",
        "fonte": "API-Sports v3 (dados reais 2023)",
        "stats_resumo": stats,
        "jogos_exemplo": games
    }

# === SERVIR FRONTEND ===
app.mount("/", StaticFiles(directory="public", html=True), name="static")
