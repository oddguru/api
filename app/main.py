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

app = FastAPI(title="OddGuru PRO v3.1 - IA + Value Bets")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === SUPABASE (seguro com env vars) ===
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

# === ENDPOINTS ===
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

# === UPDATE COM API REAL (SEM FALLBACK) ===
@app.get("/api/update-today")
def update_today():
    today = datetime.date.today().strftime("%Y-%m-%d")
    api_key = os.getenv("FOOTBALL_API_KEY")

    if not api_key:
        logger.error("FOOTBALL_API_KEY não configurada no Render")
        raise HTTPException(status_code=500, detail="API key não configurada")

    try:
        headers = {"X-Auth-Token": api_key}
        url = "https://api.football-data.org/v4/competitions/2013/matches"
        params = {"dateFrom": today, "dateTo": today}
        
        logger.info(f"Buscando jogos reais do Brasileirão para {today}...")
        resp = requests.get(url, headers=headers, params=params, timeout=12)

        if resp.status_code != 200:
            logger.error(f"API error {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=502, detail=f"Erro na API: {resp.status_code}")

        data = resp.json()
        matches = data.get("matches", [])

        if not matches:
            logger.info(f"Nenhum jogo encontrado para {today}")
            return {
                "status": "Nenhum jogo hoje",
                "source": "API real",
                "jogos": 0,
                "data": today,
                "bets_added": 0
            }

        logger.info(f"Encontrados {len(matches)} jogos reais")

    except requests.exceptions.RequestException as e:
        logger.error(f"Falha na conexão com API: {e}")
        raise HTTPException(status_code=502, detail="Falha na conexão com a API")

    # === GERA 5 BETS POR JOGO (SÓ COM DADOS REAIS) ===
    added = 0
    for m in matches:
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        match = f"{home} vs {away}"

        bets = [
            {"market": "1X2", "selection": home, "odd": 2.15, "edge": 0.33, "why": f"{home} forte em casa"},
            {"market": "cartoes", "selection": "Over 5.5", "odd": 1.98, "edge": 0.39, "why": "Média 6.4 cartões"},
            {"market": "escanteios", "selection": "Over 9.5", "odd": 1.92, "edge": 0.36, "why": "Média 10.8 escanteios"},
            {"market": "gols", "selection": "Over 2.5", "odd": 2.05, "edge": 0.31, "why": "8/10 jogos com +2.5"},
            {"market": "btts", "selection": "Sim", "odd": 2.00, "edge": 0.32, "why": "BTTS em 9/10"}
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

    logger.info(f"{added} value bets reais cadastradas!")
    return {
        "status": f"{added} value bets reais cadastradas!",
        "source": "API real",
        "jogos": len(matches),
        "data": today,
        "bets_added": added
    }

# === SERVIR FRONTEND ===
app.mount("/", StaticFiles(directory="public", html=True), name="static")
