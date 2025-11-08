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

# === JOGOS REAIS DE HOJE (06/11/2025) ===
JOGOS_HOJE = [
    {"home": "Fluminense", "away": "Mirassol", "odd_home": 1.93, "status": "19:30"},
    {"home": "Ceará", "away": "Fortaleza", "odd_home": 2.30, "status": "20:00"},
    {"home": "Palmeiras", "away": "Santos", "odd_home": 1.40, "status": "21:30"},
]

# === HISTÓRICO DE APOSTAS (AO VIVO) ===
HISTORY: List[Dict] = []

# === API: VALUE BETS ===
@app.get("/api/smart-bets")
def smart_bets() -> Dict:
    prob_home = 0.70
    value_bets = []

    for jogo in JOGOS_HOJE:
        odd_home = jogo["odd_home"]
        edge = (prob_home * odd_home) - 1

        if edge > 0.05:
            value_bets.append({
                "match": f"{jogo['home']} vs {jogo['away']}",
                "status": jogo["status"],
                "odd_home": odd_home,
                "edge": round(edge, 3),
                "suggestion": "APOSTE NO MANDANTE!"
            })

    return {
        "value_bets": value_bets,
        "total_games": len(JOGOS_HOJE),
        "api_source": "Odds reais (06/11/2025)",
        "model": "Probabilidade fixa 70% (mandante + histórico 100 jogos)"
    }

# === API: REGISTRAR RESULTADO ===
@app.post("/api/record-result")
def record_result(
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
        "date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    return {"status": "registrado", "total": len(HISTORY)}

# === API: HISTÓRICO COMPLETO ===
@app.get("/api/history")
def get_history():
    if not HISTORY:
        return {"message": "Nenhuma aposta registrada ainda. Use /api/record-result"}

    wins = len([h for h in HISTORY if h["result"] == "win"])
    total = len(HISTORY)
    profit = (wins * (odd_avg_win() - 1) * 100) - ((total - wins) * 100)
    roi = (profit / (total * 100)) if total > 0 else 0

    return {
        "total_bets": total,
        "wins": wins,
        "losses": total - wins,
        "profit": round(profit, 2),
        "roi": f"{roi*100:.1f}%",
        "history": HISTORY[-10:]  # Últimas 10
    }

def odd_avg_win():
    wins = [h for h in HISTORY if h["result"] == "win"]
    return sum(h["odd"] for h in wins) / len(wins) if wins else 2.0

# === DEBUG ===
@app.get("/api/debug")
def debug():
    return {
        "status": "API 100% viva",
        "jogos_hoje": len(JOGOS_HOJE),
        "historico": len(HISTORY),
        "render": "Online"
    }

# === SERVIR FRONTEND ===
app.mount("/", StaticFiles(directory="public", html=True), name="static")
