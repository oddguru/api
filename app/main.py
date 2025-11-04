from app.smart_bets import router as smart_router
from app.football import router as football_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import joblib
import pandas as pd
from typing import List, Dict

app = FastAPI(title="OddGuru IA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carrega modelo (lazy, só na primeira chamada)
model = None

def load_model():
    global model
    if model is None:
        model = joblib.load("model.pkl")
    return model

@app.get("/")
def home():
    return {"message": "OddGuru IA rodando com XGBoost!"}

@app.get("/api/valuebets") 
def value_bets() -> List[Dict]:
    model = load_model()
    test_data = pd.DataFrame([
        {'home_goals_last5': 12, 'away_goals_last5': 8, 'home_form': 14, 'away_form': 6, 'h2h_home_wins': 3, 'odd_home': 1.85},
        {'home_goals_last5': 9, 'away_goals_last5': 10, 'home_form': 10, 'away_form': 8, 'h2h_home_wins': 2, 'odd_home': 2.10},
    ])
    features = ['home_goals_last5', 'away_goals_last5', 'home_form', 'away_form', 'h2h_home_wins']
    probs = model.predict_proba(test_data[features])[:, 1]

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
                "suggestion": "Aposte no mandante!"
            })
    return bets
    
    app.include_router(football_router, prefix="/api")
    app.include_router(smart_router, prefix="/api")
