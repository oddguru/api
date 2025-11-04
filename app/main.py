from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import joblib
import pandas as pd
import requests
from typing import List, Dict

app = FastAPI(
    title="OddGuru IA",
    description="Value Bets com XGBoost + API-Football",
    version="3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CARREGA MODELO (CAMINHO CORRETO PARA RAIZ DO PROJETO)
import os
try:
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model.pkl")
    MODEL = joblib.load(MODEL_PATH)
    print(f"Modelo carregado com sucesso: {MODEL_PATH}")
except Exception as e:
    print(f"Erro ao carregar model.pkl: {e}")
    MODEL = None
    @app.get("/api/debug")
def debug():
    import os
    current_dir = os.path.dirname(__file__)
    root_dir = os.path.dirname(current_dir)
    model_path = os.path.join(root_dir, "model.pkl")
    
    return {
        "current_dir": current_dir,
        "root_dir": root_dir,
        "model_path": model_path,
        "model_exists": os.path.exists(model_path),
        "model_size_kb": os.path.getsize(model_path) / 1024 if os.path.exists(model_path) else 0,
        "MODEL_loaded": MODEL is not None
    }

# ROTA RAIZ
@app.get("/", include_in_schema=False)
@app.head("/", include_in_schema=False)
def home():
    return {"message": "OddGuru IA rodando com XGBoost + API-Football!"}

# VALUE BETS FIXAS
@app.get("/api/valuebets")
def value_bets() -> List[Dict]:
    if MODEL is None:
        return [{"error": "Modelo não carregado"}]

    test_data = pd.DataFrame([
        {'home_goals_last5': 12, 'away_goals_last5': 8, 'home_form': 14, 'away_form': 6, 'h2h_home_wins': 3, 'odd_home': 1.85},
        {'home_goals_last5': 9, 'away_goals_last5': 10, 'home_form': 10, 'away_form': 8, 'h2h_home_wins': 2, 'odd_home': 2.10}
    ])
    features = ['home_goals_last5', 'away_goals_last5', 'home_form', 'away_form', 'h2h_home_wins']
    probs = MODEL.predict_proba(test_data[features])[:, 1]

    bets = []
    matches = ["Flamengo vs Palmeiras", "Corinthians vs São Paulo"]
    for i, prob in enumerate(probs):
        edge = (prob * test_data.iloc[i]['odd_home']) - 1
        if edge > 0.05:
            bets.append({
                "match": matches[i],
                "prob_home": round(prob, 3),
                "odd_home": test_data.iloc[i]['odd_home'],
                "edge": round(edge, 3),
                "suggestion": "APOSTE NO MANDANTE!"
            })
    return bets or [{"message": "Nenhuma value bet fixa"}]

# SMART BETS AO VIVO
API_TOKEN = "69a4062b62f0434d966d5aad2e78a1df"
HEADERS = {"X-Auth-Token": API_TOKEN}

@app.get("/api/smart-bets")
def smart_bets() -> List[Dict]:
    if MODEL is None:
        return [{"error": "Modelo não carregado"}]

    try:
        url = "https://api.football-data.org/v4/competitions/BSA/matches?status=SCHEDULED"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return [{"error": f"API: {resp.status_code}"}]

        matches = resp.json().get("matches", [])[:5]
        bets = []

        for m in matches:
            home = m["homeTeam"]["shortName"]
            away = m["awayTeam"]["shortName"]
            odd_home = m.get("odds", {}).get("homeWin")
            if not odd_home or odd_home < 1.5: continue

            features = pd.DataFrame([{
                'home_goals_last5': 11, 'away_goals_last5': 8,
                'home_form': 12, 'away_form': 7, 'h2h_home_wins': 3
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

        return bets or [{"message": "Nenhuma value bet ao vivo. Volte em 1h!"}]

    except Exception as e:
        return [{"error": str(e)}]
