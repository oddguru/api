import xgboost as xgb
import requests
import pandas as pd
from fastapi import FastAPI
from typing import Dict, List
import os

app = FastAPI()

# CARREGA O MODELO XGBOOST
MODEL = None
model_path = os.path.join(os.path.dirname(__file__), "model.json")

try:
    if os.path.exists(model_path):
        MODEL = xgb.XGBClassifier()
        MODEL.load_model(model_path)
        print("XGBoost carregado com sucesso!")
    else:
        print(f"model.json não encontrado em: {model_path}")
except Exception as e:
    print(f"Erro ao carregar XGBoost: {e}")

@app.get("/api/smart-bets")
def smart_bets() -> Dict:
    if MODEL is None:
        return {"error": "XGBoost não carregado. Verifique model.json"}

    try:
        token = "nvaD1qrpdmhhvIvB6ExG9kL81YL71PmcgYnBuaSKh26H1895FuNrFPnEkt7b"
        url = f"https://api.sportmonks.com/v3/football/fixtures?api_token={token}&include=odds&leagues=8"  # Champions

        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return {"error": f"Sportmonks: {resp.status_code}"}

        data = resp.json().get("data", [])
        if not data:
            return {"value_bets": [{"message": "Nenhum jogo na Champions hoje"}]}

        bets = []
        debug = []

        # FEATURES DO MODELO (ajuste conforme seu treino)
        features_order = ['home_goals_last5', 'away_goals_last5', 'home_form', 'away_form', 'h2h_home_wins']

        for fixture in data[:10]:
            home = fixture["name"].split(" vs ")[0]
            away = fixture["name"].split(" vs ")[1]
            status = fixture.get("state", {}).get("name", "N/A")

            # PEGA ODD REAL (BET365)
            odd_home = 2.00
            for odd in fixture.get("odds", []):
                if odd["bookmaker"]["name"] == "Bet365" and odd["market"]["name"] == "1X2":
                    for v in odd["values"]:
                        if v["name"] == "1":
                            odd_home = float(v["odd"])
                            break
                    break

            # FEATURES FIXAS (substitua por API real depois)
            features = [11, 8, 12, 7, 3]  # [home_goals_last5, ...]
            prob_home = float(MODEL.predict_proba([features])[0][1])
            edge = (prob_home * odd_home) - 1

            debug.append({
                "match": f"{home} vs {away}",
                "status": status,
                "odd_home": round(odd_home, 2),
                "prob_home": round(prob_home, 3),
                "edge": round(edge, 3),
                "source": "Bet365" if odd_home != 2.00 else "SIMULADA"
            })

            if edge > 0.05:
                bets.append({
                    "match": f"{home} vs {away}",
                    "odd_home": round(odd_home, 2),
                    "prob_home": round(prob_home, 3),
                    "edge": round(edge, 3),
                    "suggestion": "APOSTE NO MANDANTE!"
                })

        return {
            "value_bets": bets or [{"message": "Nenhuma value bet (edge < 5%)"}],
            "debug_jogos": debug,
            "total_games": len(data),
            "api_source": "Sportmonks + XGBoost"
        }

    except Exception as e:
        return {"error": f"Erro: {str(e)}"}
