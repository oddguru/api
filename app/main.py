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

# === JOGOS DA RODADA 33 (BETANO - 08/11/2025) ===
JOGOS_HOJE = [
    {"home": "Sport Recife", "away": "Atlético-MG", "odd_home": 3.55, "status": "08/11 16:00"},
    {"home": "Vasco da Gama", "away": "Juventude", "odd_home": 1.53, "status": "08/11 16:00"},
    {"home": "Internacional", "away": "Bahia", "odd_home": 2.35, "status": "08/11 18:30"},
    {"home": "São Paulo", "away": "Bragantino", "odd_home": 1.80, "status": "08/11 21:00"},
    {"home": "Corinthians", "away": "Ceará", "odd_home": 1.67, "status": "09/11 16:00"},
    {"home": "Cruzeiro", "away": "Fluminense", "odd_home": 1.88, "status": "09/11 16:00"},
    {"home": "Vitória", "away": "Botafogo", "odd_home": 3.30, "status": "09/11 16:00"},
    {"home": "Flamengo", "away": "Santos", "odd_home": 1.33, "status": "09/11 18:30"},
    {"home": "Mirassol", "away": "Palmeiras", "odd_home": 4.10, "status": "09/11 20:30"},
    {"home": "Fortaleza", "away": "Grêmio", "odd_home": 2.10, "status": "09/11 20:30"},
]

# === POSIÇÃO NA TABELA (08/11/2025) ===
TABELA = {
    "Flamengo": 1, "Botafogo": 2, "Palmeiras": 3, "São Paulo": 4,
    "Internacional": 5, "Cruzeiro": 6, "Corinthians": 7, "Fortaleza": 8,
    "Vasco da Gama": 9, "Bahia": 10, "Atlético-MG": 11, "Grêmio": 12,
    "Vitória": 13, "Fluminense": 14, "Ceará": 15, "Juventude": 16,
    "Sport Recife": 17, "Bragantino": 18, "Santos": 19, "Mirassol": 20
}

# === HISTÓRICO DE APOSTAS ===
HISTORY: List[Dict] = []

# === API: VALUE BETS (MODELO REALISTA + FILTROS DE SEGURANÇA) ===
@app.get("/api/smart-bets")
def smart_bets() -> Dict:
    value_bets = []

    for jogo in JOGOS_HOJE:
        home = jogo["home"]
        away = jogo["away"]
        odd_home = jogo["odd_home"]
        
        # POSIÇÃO DOS TIMES
        pos_home = TABELA.get(home, 20)
        pos_away = TABELA.get(away, 20)
        
        # PROBABILIDADE BASE
        prob_home = 0.50
        
        # AJUSTES POR POSIÇÃO
        if pos_home <= 8: prob_home += 0.15   # Top 8 em casa
        if pos_home > 12: prob_home -= 0.10   # Fora do G12
        if pos_away <= 4: prob_home -= 0.12   # Visitante top 4
        if pos_home <= 4: prob_home += 0.08   # Mandante top 4
        
        # LIMITES
        prob_home = max(0.30, min(0.75, prob_home))
        
        # EDGE
        edge = (prob_home * odd_home) - 1

        # FILTROS DE SEGURANÇA (SÓ ENVIA O QUE FAZ SENTIDO)
        if (edge >= 0.15 and           # Edge realista
            odd_home <= 2.50 and       # Nada de zebra louca
            pos_home <= 12):           # Time competitivo

            value_bets.append({
                "match": f"{home} vs {away}",
                "status": jogo["status"],
                "odd_home": odd_home,
                "edge": round(edge, 3),
                "prob_home": round(prob_home, 3),
                "suggestion": "APOSTE NO MANDANTE!"
            })

    return {
        "value_bets": value_bets or [{"message": "Nenhuma value bet segura hoje. Aguarde amanhã!"}],
        "total_games": len(JOGOS_HOJE),
        "api_source": "Odds Betano (08/11/2025)",
        "model": "Tabela + posição realista + filtro de segurança"
    }

# === REGISTRAR RESULTADO (GET - 1 CLIQUE) ===
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
    return {"status": "registrado", "total": len(HISTORY)}

# === HISTÓRICO + ROI ===
@app.get("/api/history")
def get_history():
    if not HISTORY:
        return {"message": "Nenhuma aposta registrada. Use /api/record-result-get"}
    
    wins = len([h for h in HISTORY if h["result"] == "win"])
    total = len(HISTORY)
    profit = sum((h["odd"] - 1) * 100 for h in HISTORY if h["result"] == "win") - ((total - wins) * 100)
    roi = (profit / (total * 100)) if total > 0 else 0

    return {
        "total_bets": total,
        "wins": wins,
        "losses": total - wins,
        "profit": round(profit, 2),
        "roi": f"{roi*100:.1f}%",
        "history": HISTORY[-10:]
    }

# === DEBUG ===
@app.get("/api/debug")
def debug():
    return {
        "status": "API 100% viva",
        "jogos_hoje": len(JOGOS_HOJE),
        "historico": len(HISTORY),
        "model": "Tabela + filtro de segurança"
    }

# === SERVIR FRONTEND ===
app.mount("/", StaticFiles(directory="public", html=True), name="static")
