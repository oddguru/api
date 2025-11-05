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
# DEBUG ENDPOINT (SEM NUMPY)
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
        "classes": [int(c) for c in MODEL.classes_] if MODEL and hasattr(MODEL, 'classes_') else None,
        "features": [str(f) for f in MODEL.feature_names_in_] if MODEL and hasattr(MODEL, 'feature_names_in_') else None
    }

# =============================
# ROTA RAIZ
# =============================
@app.get("/", include_in_schema=False)
@app.head("/", include_in_schema=False)
def home():
    return {"message": "OddGuru IA rodando com XGBoost + API-Football!"}

# =============================
# VALUE BETS FIXAS (SEM NUMPY)
# =============================
@app.get("/api/valuebets")
def value_bets() -> List[Dict]:
    if MODEL is None:
        return [{"error": "Modelo XGBoost não carregado"}]

    try:
        features_order = ['home_goals_last5', 'away_goals_last5', 'home_form', 'away_form', 'h2h_home_wins']
        test_data = pd.DataFrame([
            [12, 8, 14, 6, 3, 1.85],
            [9, 10, 10, 8, 2, 2.10]
        ], columns=features_order + ['odd_home'])

        X = test_data[features_order]
        probs = MODEL.predict_proba(X)[:, 1]

        bets = []
        matches = ["Flamengo vs Palmeiras", "Corinthians vs São Paulo"]
        for i, prob in enumerate(probs):
            prob = float(prob)  # CONVERTE numpy.float32 → float
            odd = float(test_data.iloc[i]['odd_home'])
            edge = (prob * odd) - 1
            if edge > 0.05:
                bets.append({
                    "match": matches[i],
                    "prob_home": round(prob, 3),
                    "odd_home": round(odd, 2),
                    "edge": round(edge, 3),
                    "suggestion": "APOSTE NO MANDANTE!"
                })
        return bets or [{"message": "Nenhuma value bet fixa hoje"}]

    except Exception as e:
        print(f"ERRO EM value_bets: {str(e)}")
        return [{"error": f"Erro: {str(e)}"}]

# =============================
# SMART BETS AO VIVO (SEM NUMPY)
# =============================
@app.get("/api/smart-bets")
def smart_bets() -> Dict:
    if MODEL is None:
        return {"error": "Modelo XGBoost não carregado"}

    try:
        # THE ODDS API (FREE 500 req/mês)
        api_key = "3ca7df5885f44c6524d0cec01380be26"
        url = f"https://api.the-odds-api.com/v4/sports/soccer_uefa_champs_league/odds/?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
        resp = requests.get(url, timeout=15)
        
        if resp.status_code != 200:
            return {"error": f"The Odds API: {resp.status_code}"}

        matches = resp.json()
        bets = []
        debug = []

        features_order = ['home_goals_last5', 'away_goals_last5', 'home_form', 'away_form', 'h2h_home_wins']

        for match in matches[:10]:
            home = match["home_team"]
            away = match["away_team"]
            odd_home = None

            # PEGA A MELHOR ODD HOME (média ou Bet365)
            for book in match.get("bookmakers", []):
                if book["key"] == "bet365":  # Prioriza Bet365
                    for market in book.get("markets", []):
                        if market["key"] == "h2h":
                            for outcome in market.get("outcomes", []):
                                if outcome["name"] == home:
                                    odd_home = outcome["price"]
                                    break
                            if odd_home: break
                    if odd_home: break

            if not odd_home:
                continue  # Pula se não tiver odd

            # DADOS FIXOS (ajustar depois com API-Football stats)
            features_df = pd.DataFrame([{
                'home_goals_last5': 12, 'away_goals_last5': 8,
                'home_form': 13, 'away_form': 7, 'h2h_home_wins': 3
            }])[features_order]

            prob = float(MODEL.predict_proba(features_df)[0][1])
            edge = (prob * odd_home) - 1

            debug.append({
                "match": f"{home} vs {away}",
                "odd_home": round(odd_home, 2),
                "prob_home": round(prob, 3),
                "edge": round(edge, 3)
            })

            if edge > 0.05:
                bets.append({
                    "match": f"{home} vs {away}",
                    "prob_home": round(prob, 3),
                    "odd_home": round(odd_home, 2),
                    "edge": round(edge, 3),
                    "suggestion": "APOSTE NO MANDANTE!"
                })

        return {
            "value_bets": bets or [{"message": "Nenhuma value bet (aguardando jogos com odds)"}],
            "debug_jogos": debug,
            "api_source": "The Odds API (free)",
            "requests_remaining": resp.headers.get("X-Requests-Remaining", "N/A")
        }

    except Exception as e:
        print(f"ERRO EM smart_bets: {str(e)}")
        return {"error": f"Erro: {str(e)}"}
