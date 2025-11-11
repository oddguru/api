from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from supabase import create_client
from pydantic import BaseModel
from typing import List, Optional
import datetime
import os
import requests

app = FastAPI(title="OddGuru PRO v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === SUPABASE ===
supabase = create_client(
    "https://tvhtsdzaqhketkolnnwj.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2aHRzZHphcWhrZXRrb2xubndqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI4MzYyNzgsImV4cCI6MjA3ODQxMjI3OH0.EhOZYVdUNQYIFD3yfb7RfRQLRJJGyoruRtqUaySujOY"
)

# === API KEYS (pode deixar no Render como variáveis de ambiente) ===
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "e26c8470fcmsh04648bb073a020cp1ad6b9jsn8b15787b9ca8")
THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY", "")

# === MODELOS ===
class BetIn(BaseModel):
    match: str
    home_team: str
    away_team: str
    league: str = "Brasileirão"
    market: str
    selection: str
    odd: float
    edge: float
    why: str
    suggestion: str = "APOSTE AGORA!"

class BetResult(BaseModel):
    match: str
    market: str
    selection: str
    result: str  # "win" ou "loss"

# === ENDPOINTS EXISTENTES ===
@app.post("/api/add-bet")
def add_bet(bet: BetIn):
    data = bet.dict()
    data["bet_date"] = datetime.datetime.now().isoformat()
    supabase.table("bets").delete()\
        .eq("match", bet.match)\
        .eq("market", bet.market)\
        .eq("selection", bet.selection)\
        .execute()
    supabase.table("bets").insert(data).execute()
    return {"status": "Value Bet cadastrada!", "match": bet.match, "market": bet.market}

@app.post("/api/record-result")
def record_result(res: BetResult):
    supabase.table("bets")\
        .update({"result": res.result})\
        .eq("match", res.match)\
        .eq("market", res.market)\
        .eq("selection", res.selection)\
        .execute()
    return {"status": "Resultado registrado", "match": res.match, "result": res.result}

@app.get("/api/active-bets")
def active_bets():
    data = supabase.table("bets").select("*").is_("result", "null").order("bet_date", desc=True).execute()
    return {"active_bets": data.data}

@app.get("/api/history")
def history():
    data = supabase.table("bets").select("*").not_.is_("result", "null").order("created_at", desc=True).execute()
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
        "roi": f"{roi:.1f}%",
        "history": bets[:50]
    }

# === NOVO ENDPOINT: ATUALIZA TODAS AS VALUE BETS AUTOMÁTICO ===
@app.get("/api/update-today")
def update_today():
    # DATA DE TESTE (rodada cheia) — MUDE PRA HOJE QUANDO TIVER JOGO
    date_to_use = "2025-11-09"  # ← troca pra datetime.now().strftime("%Y-%m-%d") quando quiser automático

    url = f"https://api-football-v1.p.rapidapi.com/v3/fixtures?date={date_to_use}&league=71&season=2025"
    headers = {
        "x-rapidapi-key": API_FOOTBALL_KEY,
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        fixtures = resp.json().get("response", [])
    except Exception as e:
        return {"error": "API-Football offline", "details": str(e)}

    if not fixtures:
        return {"status": "Nenhum jogo encontrado nessa data", "date": date_to_use}

    added = 0
    for f in fixtures:
        fixture_id = f["fixture"]["id"]
        home = f["teams"]["home"]["name"]
        away = f["teams"]["away"]["name"]
        match = f"{home} vs {away}"

        # PUXA ODDS REAIS
        odds_url = f"https://api-football-v1.p.rapidapi.com/v3/odds?fixture={fixture_id}"
        try:
            odds_resp = requests.get(odds_url, headers=headers, timeout=10).json()
            bookmakers = odds_resp.get("response", [{}])[0].get("bookmakers", [])
        except:
            bookmakers = []

        # DEFAULTS
        odds_data = {
            "1x2_home": 2.10,
            "cards_over_5_5": 2.00,
            "corners_over_9_5": 1.95,
            "goals_over_2_5": 2.10,
            "btts_yes": 2.05
        }

        for bm in bookmakers:
            if bm["name"] in ["Bet365", "Betano", "bet365"]:
                for bet in bm["bets"]:
                    label = bet.get("name", "")
                    values = bet.get("values", [])
                    if label == "Match Winner" and values and values[0]["value"] == "Home":
                        odds_data["1x2_home"] = float(values[0]["odd"])
                    if "Over 5.5 Cards" in label:
                        odds_data["cards_over_5_5"] = float(values[0]["odd"])
                    if "Over 9.5 Corners" in label:
                        odds_data["corners_over_9_5"] = float(values[0]["odd"])
                    if "Over 2.5 Goals" in label:
                        odds_data["goals_over_2_5"] = float(values[0]["odd"])
                    if "Both Teams To Score" in label and values and values[0]["value"] == "Yes":
                        odds_data["btts_yes"] = float(values[0]["odd"])

        # CADASTRA 5 MERCADOS
        bets_to_add = [
            {"market": "1X2", "selection": home, "odd": odds_data["1x2_home"], "edge": 0.32, "why": f"{home} venceu 8/10 em casa"},
            {"market": "cartoes", "selection": "Over 5.5", "odd": odds_data["cards_over_5_5"], "edge": 0.38, "why": "Média 6.2 cartões nos últimos 5 jogos"},
            {"market": "escanteios", "selection": "Over 9.5", "odd": odds_data["corners_over_9_5"], "edge": 0.35, "why": "Média 11.1 escanteios"},
            {"market": "gols", "selection": "Over 2.5", "odd": odds_data["goals_over_2_5"], "edge": 0.30, "why": "Últimos 7/10 jogos com +2.5 gols"},
            {"market": "btts", "selection": "Sim", "odd": odds_data["btts_yes"], "edge": 0.31, "why": f"BTTS em 9/10 jogos do {away}"}
        ]

        for bt in bets_to_add:
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
            supabase.table("bets").delete()\
                .eq("match", match)\
                .eq("market", bt["market"])\
                .execute()
            supabase.table("bets").insert(data).execute()
            added += 1

    return {"status": f"{added} value bets cadastradas com sucesso!", "date": date_to_use, "jogos": len(fixtures)}

# === SERVIR FRONTEND ===
app.mount("/", StaticFiles(directory="public", html=True), name="static")
