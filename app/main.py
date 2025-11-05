from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from typing import Dict, List
from datetime import datetime

app = FastAPI(title="OddGuru MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

headers = {
    "x-rapidapi-key": "e26c8470fcmsh04648bb073a020cp1ad6b9jsn8b15787b9ca8",
    "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
}

@app.get("/")
def home():
    return {"message": "OddGuru MVP ao vivo — jogos reais + edge!"}

@app.get("/api/smart-bets")
def smart_bets() -> Dict:
    try:
        # JOGOS AO VIVO (GRÁTIS)
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures?live=all"
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code != 200:
            return {"error": f"API-Football: {resp.status_code}"}

        fixtures = resp.json().get("response", [])
        if not fixtures:
            return {"value_bets": [{"message": "Nenhum jogo ao vivo no momento"}]}

        # Filtra Champions e Brasileirão
        fixtures = [f for f in fixtures if f["league"]["id"] in [2, 71]]

        bets = []
        debug = []

        for fixture in fixtures[:10]:
            home = fixture["teams"]["home"]["name"]
            away = fixture["teams"]["away"]["name"]
            status = fixture["fixture"]["status"]["long"]

            # ODDS SIMULADAS (MVP — substituir por odds reais depois)
            odd_home = 2.00
            prob_home = 0.70
            edge = (prob_home * odd_home) - 1

            debug.append({
                "match": f"{home} vs {away}",
                "status": status,
                "odd_home": odd_home,
                "prob_home": prob_home,
                "edge": round(edge, 3)
            })

            if edge > 0.05:
                bets.append({
                    "match": f"{home} vs {away}",
                    "prob_home": prob_home,
                    "odd_home": odd_home,
                    "edge": round(edge, 3),
                    "suggestion": "APOSTE NO MANDANTE!"
                })

        return {
            "value_bets": bets or [{"message": "Nenhuma value bet (edge < 5%)"}],
            "debug_jogos": debug,
            "total_games": len(fixtures),
            "api_source": "API-Football Free (jogos ao vivo)"
        }

    except Exception as e:
        return {"error": f"Erro: {str(e)}"}
