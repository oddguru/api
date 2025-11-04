import requests
import joblib
import pandas as pd
from fastapi import APIRouter

router = APIRouter()
TOKEN = "69a4062b62f0434d966d5aad2e78a1df"  # Seu token
HEADERS = {"X-Auth-Token": TOKEN}
MODEL = joblib.load("model.pkl")  # Seu modelo treinado

@router.get("/smart-bets")
def smart_bets():
    try:
        # Puxa jogos do Brasileirão (próximos)
        url = "https://api.football-data.org/v4/competitions/BSA/matches?status=SCHEDULED"
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            return [{"error": "API Football offline ou limite (0 req usadas hoje)"}]

        matches = resp.json().get("matches", [])[:5]  # 5 jogos futuros

        bets = []
        for m in matches:
            home = m["homeTeam"]["shortName"]
            away = m["awayTeam"]["shortName"]
            odds = m.get("odds", {})
            odd_home = odds.get("homeWin", 0)
            if odd_home < 1.5: continue  # Só odds válidas

            # Features simuladas (baseadas em dados reais — expanda depois)
            features = pd.DataFrame([{
                'home_goals_last5': 11,  # Média recente
                'away_goals_last5': 8,
                'home_form': 12,  # Pontos nos últimos 5 jogos
                'away_form': 7,
                'h2h_home_wins': 3  # Vitórias H2H
            }])
            prob = MODEL.predict_proba(features)[0][1]
            edge = (prob * odd_home) - 1

            if edge > 0.05:  # Edge > 5%
                bets.append({
                    "match": f"{home} vs {away}",
                    "prob_home": round(prob, 3),
                    "odd_home": round(odd_home, 2),
                    "edge": round(edge, 3),
                    "suggestion": "APOSTE NO MANDANTE!" if edge > 0.10 else "Value moderada"
                })

        return bets if bets else [{"message": "Nenhuma value bet hoje. Verifique amanhã!"}]
    except Exception as e:
        return [{"error": f"Erro interno: {str(e)}"}]
