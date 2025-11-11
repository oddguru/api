from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from supabase import create_client
from pydantic import BaseModel
from typing import List, Optional
import datetime
import os

app = FastAPI(title="OddGuru PRO v2")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === SUPABASE (SUAS CHAVES JÁ ESTÃO AQUI) ===
supabase = create_client(
    "https://tvhtsdzaqhketkolnnwj.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2aHRzZHphcWhrZXRrb2xubndqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI4MzYyNzgsImV4cCI6MjA3ODQxMjI3OH0.EhOZYVdUNQYIFD3yfb7RfRQLRJJGyoruRtqUaySujOY"
)

# === MODELOS ===
class BetIn(BaseModel):
    match: str
    home_team: str
    away_team: str
    league: str = "Brasileirão"
    market: str  # 1X2, cartoes, escanteios, gols, btts, over1.5
    selection: str  # "São Paulo", "Over 5.5", "BTTS Sim", etc
    odd: float
    edge: float
    why: str
    suggestion: str = "APOSTE AGORA!"

class BetResult(BaseModel):
    match: str
    market: str
    selection: str
    result: str  # "win" ou "loss"

# === CADASTRAR NOVA VALUE BET ===
@app.post("/api/add-bet")
def add_bet(bet: BetIn):
    data = bet.dict()
    data["bet_date"] = datetime.datetime.now().isoformat()
    
    # Remove se já existir exatamente a mesma aposta
    supabase.table("bets").delete()\
        .eq("match", bet.match)\
        .eq("market", bet.market)\
        .eq("selection", bet.selection)\
        .execute()
    
    supabase.table("bets").insert(data).execute()
    return {"status": "Value Bet cadastrada!", "match": bet.match, "market": bet.market}

# === REGISTRAR RESULTADO ===
@app.post("/api/record-result")
def record_result(res: BetResult):
    supabase.table("bets")\
        .update({"result": res.result})\
        .eq("match", res.match)\
        .eq("market", res.market)\
        .eq("selection", res.selection)\
        .execute()
    return {"status": "Resultado registrado", "match": res.match, "result": res.result}

# === TODAS AS APOSTAS ATIVAS (CORRIGIDO) ===
@app.get("/api/active-bets")
def active_bets():
    data = supabase.table("bets")\
        .select("*")\
        .is_("result", "null")\
        .order("bet_date", desc=True)\
        .execute()
    return {"active_bets": data.data}

# === HISTÓRICO + ROI (CORRIGIDO) ===
@app.get("/api/history")
def history():
    data = supabase.table("bets")\
        .select("*")\
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
        "roi": f"{roi:.1f}%",
        "history": bets[:50]
    }

# === SERVIR FRONTEND ===
app.mount("/", StaticFiles(directory="public", html=True), name="static")
