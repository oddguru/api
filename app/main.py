from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict

app = FastAPI(title="OddGuru MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JOGOS + ODDS REAIS DE HOJE (06/11/2025)
JOGOS_HOJE = [
    {"home": "Fluminense", "away": "Mirassol", "odd_home": 1.93, "status": "19:30"},
    {"home": "Ceará", "away": "Fortaleza", "odd_home": 2.30, "status": "20:00"},
    {"home": "Palmeiras", "away": "Santos", "odd_home": 1.40, "status": "21:30"},
]

@app.get("/api/smart-bets")
def smart_bets() -> Dict:
    prob_home = 0.70
    value_bets = []
    all_games = []

    for jogo in JOGOS_HOJE:
        odd_home = jogo["odd_home"]
        edge = (prob_home * odd_home) - 1

        game_info = {
            "match": f"{jogo['home']} vs {jogo['away']}",
            "status": jogo["status"],
            "odd_home": odd_home,
            "edge": round(edge, 3)
        }
        all_games.append(game_info)

        # SÓ ADICIONA COMO VALUE BET SE EDGE > 5%
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
        "all_games": all_games,  # Todos os jogos (com edge negativo também)
        "total_games": len(JOGOS_HOJE),
        "api_source": "Odds reais (06/11/2025)"
    }

# SERVIR FRONTEND
app.mount("/", StaticFiles(directory="public", html=True), name="static")
