from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from typing import Dict, List

app = FastAPI(title="OddGuru MVP")

# CORS para frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "OddGuru MVP ao vivo — odds reais + edge!"}

@app.get("/api/smart-bets")
def smart_bets() -> Dict:
    try:
        # 1. RAPIDAPI - JOGOS DO DIA (FREE)
        headers = {
            "x-rapidapi-key": "e26c8470fcmsh04648bb073a020cp1ad6b9jsn8b15787b9ca8",
            "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
        }
        today = "2025-11-05"
        url = f"https://api-football-v1.p.rapidapi.com/v3/fixtures?date={today}"
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code != 200:
            return {"error": f"RapidAPI: {resp.status_code}"}

        fixtures = resp.json().get("response", [])
        fixtures = [f for f in fixtures if f["league"]["id"] in [2, 71]]  # Champions + Brasileirão

        if not fixtures:
            return {"value_bets": [{"message": "Nenhum jogo hoje"}], "total_games": 0}

        # 2. THE ODDS API - ODDS REAIS (FREE)
        odds_api_key = "3ca7df5885f44c6524d0cec01380be26"
        odds_url = f"https://api.the-odds-api.com/v4/sports/soccer_brazil_serie_a/odds/?apiKey={odds_api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
        odds_resp = requests.get(odds_url, timeout=10)

        odds_data = {}
        if odds_resp.status_code == 200:
            for match in odds_resp.json():
                key = f"{match['home_team']} vs {match['away_team']}"
                odd_home = None
                for book in match.get("bookmakers", []):
                    if book["key"] == "bet365":
                        for outcome in book["markets"][0]["outcomes"]:
                            if outcome["name"] == match["home_team"]:
                                odd_home = outcome["price"]
                                break
                        if odd_home: break
                if odd_home:
                    odds_data[key] = odd_home

        bets = []
        debug = []

        for fixture in fixtures[:10]:
            home = fixture["teams"]["home"]["name"]
            away = fixture["teams"]["away"]["name"]
            status = fixture["fixture"]["status"]["long"]
            match_key = f"{home} vs {away}"

            odd_home = odds_data.get(match_key, 2.00)  # Fallback se não tiver

            prob_home = 0.70
            edge = (prob_home * odd_home) - 1

            debug.append({
                "match": match_key,
                "status": status,
                "odd_home": round(odd_home, 2),
                "source": "The Odds API" if odd_home != 2.00 else "Fallback",
                "edge": round(edge, 3)
            })

            if edge > 0.05:
                bets.append({
                    "match": match_key,
                    "prob_home": prob_home,
                    "odd_home": round(odd_home, 2),
                    "edge": round(edge, 3),
                    "suggestion": "APOSTE NO MANDANTE!"
                })

        return {
            "value_bets": bets or [{"message": "Nenhuma value bet (edge < 5%)"}],
            "debug_jogos": debug,
            "total_games": len(fixtures),
            "api_source": "RapidAPI + The Odds API (Free Tier)"
        }

    except Exception as e:
        return {"error": f"Erro: {str(e)}"}

@app.get("/api/debug")
def debug():
    return {"status": "MVP ao vivo — Brasileirão + Champions", "api": "RapidAPI + The Odds API"}
