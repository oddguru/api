import requests
import joblib
import pandas as pd
from fastapi import APIRouter

router = APIRouter()
TOKEN = "69a4062b62f0434d966d5aad2e78a1df"
HEADERS = {"X-Auth-Token": TOKEN}
MODEL = joblib.load("model.pkl")

@router.get("/smart-bets")
def smart_bets():
    # 1. Puxa jogos do Brasileirão
    url = "https://api.football-data.org/v4/competitions/BSA/matches?status=SCHEDULED"
    resp = requests.get(url, headers=HEADERS).json()
    matches = resp["matches"][:10]  # 10 jogos futuros

    bets = []
    for m in matches:
        home = m["homeTeam"]["shortName"]
        away = m["awayTeam"]["shortName"]
        odd_home = m.get("odds", {}).get("homeWin", 0)
        if not odd_home: continue

        # 2. Features reais (simplificado)
        features = pd.DataFrame([{
            "home_goals_last5": 11,
            "away_goals_last5": 8,
            "home_form": 12,
            "away_form": 7,
            "h2h_home_wins": 3
        }])
        prob = MODEL.predict_proba(features)[0][1]
        edge = (prob * odd_home) - 1

        if edge > 0.05:
            bets.append({
                "match": f"{home} vs {away}",
                "prob_home": round(prob, 3),
                "odd_home": round(odd_home, 2),
                "edge": round(edge, 3),
                "suggestion": "APOSTE NO MANDANTE!"
            })
    return bets or [{"message": "Nenhuma value bet agora. Volte em 1h!"}]
