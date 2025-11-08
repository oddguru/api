from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict, List
import datetime

app = FastAPI(title="OddGuru MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === JOGOS REAIS ===
JOGOS_HOJE = [
    {"home": "Fluminense", "away": "Mirassol", "odd_home": 1.93, "status": "19:30"},
    {"home": "Ceará", "away": "Fortaleza", "odd_home": 2.30, "status": "20:00"},
    {"home": "Palmeiras", "away": "Santos", "odd_home": 1.40, "status": "21:30"},
]

# === HISTÓRICO ===
HISTORY: List[Dict] = []

# === VALUE BETS ===
@app.get("/api/smart-bets")
def smart_bets():
    prob_home = 0.70
    value_bets = []
    for jogo in JOGOS_HOJE:
        edge = (prob_home * jogo["odd_home"]) - 1
        if edge > 0.05:
            value_bets.append({
                "match": f"{jogo['home']} vs {jogo['away']}",
                "status": jogo["status"],
                "odd_home": jogo["odd_home"],
                "edge": round(edge, 3),
                "suggestion": "APOSTE NO MANDANTE!"
            })
    return {"value_bets": value_bets}

# === REGISTRAR COM GET (1 CLIQUE!) ===
@app.get("/api/record-result-get")
def record_result_get(
    match: str = Query(...),
    odd: float = Query(...),
    edge: float = Query(...),
    result: str = Query(..., regex="^(win|loss)$")
):
    global HISTORY
    HISTORY.append({
        "match": match,
        "odd": odd,
        "edge": round(edge, 3),
        "result": result,
        "date": datetime.datetime.now().strftime("%d/%m %H:%M")
    })
    return {"status": "registrado com GET", "total": len(HISTORY)}

# === HISTÓRICO ===
@app.get("/api/history")
def get_history():
    if not HISTORY:
        return {"message": "Nenhuma aposta registrada. Use /api/record-result-get"}
    wins = len([h for h in HISTORY if h["result"] == "win"])
    total = len(HISTORY)
    profit = sum(h["odd"]-1 for h in HISTORY if h["result"] == "win") * 100 - (total - wins) * 100
    roi = profit / (total * 100) if total > 0 else 0
    return {
        "total_bets": total,
        "wins": wins,
        "profit": round(profit, 2),
        "roi": f"{roi*100:.1f}%",
        "history": HISTORY[-10:]
    }

# === DEBUG ===
@app.get("/api/debug")
def debug():
    return {"status": "API viva", "historico": len(HISTORY)}

app.mount("/", StaticFiles(directory="public", html=True), name="static")
