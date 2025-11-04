from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from xgboost import XGBClassifier
import pandas as pd
import requests
import os
from typing import List, Dict

# =============================
# APP + CORS
# =============================
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

# =============================
# CARREGA MODELO (JSON)
# =============================
try:
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model.json")
    MODEL = XGBClassifier()
    MODEL.load_model(MODEL_PATH)
    print(f"Modelo JSON carregado com sucesso: {MODEL_PATH}")
except Exception as e:
    print(f"Erro ao carregar model.json: {e}")
    MODEL = None

# =============================
# DEBUG ENDPOINT
# =============================
@app.get("/api/debug")
def debug():
    current_dir = os.path.dirname(__file__)
    root_dir = os.path.dirname(current_dir)
    model_path = os.path.join(root_dir, "model.json")
    
    return {
        "current_dir": current_dir,
        "root_dir": root_dir,
        "model_path": model_path,
        "model_exists": os.path.exists(model_path),
        "model_size_kb": round(os.path.getsize(model_path) / 1024, 2) if os.path.exists(model_path) else 0,
        "MODEL_loaded": MODEL is not None,
        "classes": list(MODEL.classes_) if MODEL and hasattr(MODEL, 'classes_') else None,
        "features": list(MODEL.feature_names_in_) if MODEL and hasattr(MODEL, 'feature_names_in_') else None
    }

# =============================
# ROTA RAIZ
# =============================
@app.get("/", include_in_schema=False)
@app.head("/", include_in_schema=False)
def home():
    return {"message": "OddGuru IA rodando com XGBoost + API-Football!"}

# =============================
# VALUE BETS FIXAS (ORDEM EXATA)
# =============================
@app.get("/api/valuebets")
def value_bets() -> List[Dict]:
    if MODEL is None:
        return [{"error": "Modelo XGBoost não carregado"}]

    try:
        # ORDEM EXATA DAS FEATURES
        features_order = ['home_goals_last5', 'away_goals_last5', 'home_form', 'away_form', 'h2h_home_wins']
        test_data = pd.DataFrame([
            [12, 8, 14, 6, 3, 1.85],
            [9, 10, 10, 8, 2, 2.10]
        ], columns=features_order + ['odd_home'])

        X = test_data[features_order]
        probs = MODEL.predict_proba(X)[:, 1]  # 1 = vitória do mandante

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
        return bets or [{"message": "Nenhuma value bet fixa hoje"}]

    except Exception as e:
        print(f"ERRO EM value_bets: {str(e)}")
        return [{"error": f"Erro: {str(e)}"}]

# =============================
# SMART BETS AO VIVO (ORDEM EXATA)
# =============================
API_TOKEN = "69a4062b62f0434d966d5aad2e78a1df"
HEADERS = {"X-Auth-Token": API_TOKEN}

@app.get("/api/smart-bets")
def smart_bets() -> List[Dict]:
    if MODEL is None:
        return [{"error": "Modelo XGBoost não carregado"}]

    try:
        url = "https://api.football-data.org/v4/competitions/BSA/matches?status=SCHEDULED"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return [{"error": f"API Football: {resp.status_code}"}]

        matches = resp.json().get("matches", [])[:5]
        bets = []

        features_order = ['home_goals_last5', 'away_goals_last5', 'home_form', 'away_form', 'h2h_home_wins']

        for m in matches:
            home = m["homeTeam"]["shortName"]
            away = m["awayTeam"]["shortName"]
            odd_home = m.get("odds", {}).get("homeWin")
            if not odd_home or odd_home < 1.5:
                continue

            # ORDEM EXATA
            features_df = pd.DataFrame([{
                'home_goals_last5': 11, 'away_goals_last5': 8,
                'home_form': 12, 'away_form': 7, 'h2h_home_wins': 3
            }])[features_order]

            prob = MODEL.predict_proba(features_df)[0][1]
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
        return [{"error": f"Erro na API: {str(e)}"}]
