from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from supabase import create_client
from pydantic import BaseModel
import datetime
import requests
import os

app = FastAPI(title="OddGuru PRO v2")

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== SUPABASE =====
supabase = create_client(
    os.getenv("SUPABASE_URL", "https://tvhtsdzaqhketkolnnwj.supabase.co"),
    os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
)

# ===== MODELOS =====
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

# ===== ROTAS =====

@app.post("/api/add-bet")
def add_bet(bet: BetIn):
    data = bet.dict()
    data["bet_date"] = datetime.datetime.now().isoformat()
    supabase.table("bets").delete().eq("match", bet.match).eq("market", bet.market).eq("selection", bet.selection).execute()
    supabase.table("bets").insert(data).execute()
    return {"status": "Value Bet cadastrada!"}

@app.post("/api/record-result")
def record_result(res: BetResult):
    supabase.table("bets").update({"result": res.result}).eq("match", res.match).eq("market", res.market).eq("selection", res.selection).execute()
    return {"status": "Resultado registrado"}

@app.get("/api/active-bets")
def active_bets():
    data = supabase.table("bets").select("*").is_("result", None).order("bet_date", desc=True).execute()
    return {"active_bets": data.data}

@app.get("/api/history")
def history():
    data = supabase.table("bets").select("*").not_.is_("result", None).order("created_at", desc=True).execute()
    bets = data.data
    total = len(bets)
    wins = len([b for b in bets if b["result"] == "win"])
    profit = sum((b["odd"] - 1) * 100 for b in bets if b["result"] == "win") - (total - wins) * 100
    roi = (profit / (total * 100) * 100) if total > 0 else 0
    return {
        "total_bets": total, "wins": wins, "losses": total - wins,
        "profit": round(profit, 2), "roi": f"{roi:.1f}%", "history": bets[:50]
    }

# ===== FOOTBALL DATA =====
@app.get("/api/update-today")
def update_today():
    date_to_use = datetime.datetime.now().strftime("%Y-%m-%d")

    url = f"https://api.football-data.org/v4/competitions/BSA/matches?dateFrom={date_to_use}&dateTo={date_to_use}"
    headers = {"X-Auth-Token": os.getenv("FOOTBALL_API_KEY", "69a4062b62f0434d966d5aad2e78a1df")}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        matches = resp.json().get("matches", [])
    except Exception as e:
        return {"error": "API offline", "details": str(e)}

    if not matches:
        return {"status": "Sem jogos na data", "date": date_to_use}

    added = 0
    for m in matches:
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        match = f"{home} vs {away}"

        bets = [
            {"market": "1X2", "selection": home, "odd": 2.15, "edge": 0.33, "why": f"{home} forte em casa"},
            {"market": "cartoes", "selection": "Over 5.5", "odd": 1.98, "edge": 0.39, "why": "Média alta de cartões"},
            {"market": "escanteios", "selection": "Over 9.5", "odd": 1.92, "edge": 0.36, "why": "Jogo de muita posse"},
            {"market": "gols", "selection": "Over 2.5", "odd": 2.05, "edge": 0.31, "why": "Histórico de gols"},
            {"market": "btts", "selection": "Sim", "odd": 2.00, "edge": 0.32, "why": "Ambos marcam"}
        ]

        for bt in bets:
            data = {
                "match": match,
                "home_team": home,
                "away_team": away,
                "market": bt["market"],
                "selection": bt["selection"],
                "odd": bt["odd"],
                "edge": bt["edge"],
                "why": bt["why"],
                "bet_date": datetime.datetime.now().isoformat()
            }
            supabase.table("bets").delete().eq("match", match).eq("market", bt["market"]).execute()
            supabase.table("bets").insert(data).execute()
            added += 1

    return {"status": f"{added} value bets cadastradas!", "jogos": len(matches)}

# ===== FRONT =====
app.mount("/", StaticFiles(directory="public", html=True), name="static")
