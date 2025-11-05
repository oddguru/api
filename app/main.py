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
# REMOVA O XGBoost
MODEL = None

@app.get("/api/smart-bets")
def smart_bets() -> Dict:
    try:
        headers = {
            "x-rapidapi-key": "e26c8470fcmsh04648bb073a020cp1ad6b9jsn8b15787b9ca8",
            "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
        }

        # ENDPOINT GRÁTIS: JOGOS DO DIA
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://api-football-v1.p.rapidapi.com/v3/fixtures?date={today}"
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code != 200:
            return {"error": f"API-Football: {resp.status_code}"}

        fixtures = resp.json().get("response", [])
        # Filtra Champions e Brasileirão
        fixtures = [f for f in fixtures if f["league"]["id"] in [2, 71]]
        
        if not fixtures:
            return {"value_bets": [{"message": "Nenhum jogo hoje"}]}

        bets = []
        debug = []

        for fixture in fixtures[:10]:
            home = fixture["teams"]["home"]["name"]
            away = fixture["teams"]["away"]["name"]
            status = fixture["fixture"]["status"]["long"]
            fixture_id = fixture["fixture"]["id"]

            # TENTA PEGAR ODDS DO PRÓPRIO FIXTURE (GRÁTIS)
            odd_home = None
            if "bookmakers" in fixture and fixture["bookmakers"]:
                for book in fixture["bookmakers"]:
                    for bet in book.get("bets", []):
                        if bet["name"] == "Match Winner":
                            for v in bet["values"]:
                                if v["value"] == "Home":
                                    odd_home = float(v["odd"])
                                    break
                    if odd_home: break

            # Se não tiver, usa 2.00 (fallback)
            if not odd_home:
                odd_home = 2.00

            prob_home = 0.70
            edge = (prob_home * odd_home) - 1

            debug.append({
                "match": f"{home} vs {away}",
                "status": status,
                "odd_home": round(odd_home, 2),
                "prob_home": prob_home,
                "edge": round(edge, 3)
            })

            if edge > 0.05:
                bets.append({
                    "match": f"{home} vs {away}",
                    "prob_home": prob_home,
                    "odd_home": round(odd_home, 2),
                    "edge": round(edge, 3),
                    "suggestion": "APOSTE NO MANDANTE!"
                })

        return {
            "value_bets": bets or [{"message": "Nenhuma value bet (edge < 5%)"}],
            "debug_jogos": debug,
            "total_games": len(fixtures)
        }

    except Exception as e:
        return {"error": f"Erro: {str(e)}"}
