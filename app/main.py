from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import joblib
import pandas as pd

app = FastAPI(title="OddGuru IA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carrega o modelo XGBoost
model = joblib.load("model.pkl")

@app.get("/")
def home():
    return {"message": "OddGuru IA rodando com XGBoost ao vivo!"}

@app.get("/api/valuebets")
def value_bets():
    # Exemplo de features para 3 jogos reais (próximos do Brasileirão)
    test_data = pd.DataFrame([
        {'home_goals_last5': 12, 'away_goals_last5': 8, 'home_form': 14, 'away_form': 6, 'h2h_home_wins': 3, 'odd_home': 1.85},  # Flamengo vs Palmeiras
        {'home_goals_last5': 9, 'away_goals_last5': 10, 'home_form': 10, 'away_form': 8, 'h2h_home_wins': 2, 'odd_home': 2.10},  # Corinthians vs São Paulo
        {'home_goals_last5': 11, 'away_goals_last5': 7, 'home_form': 12, 'away_form': 5, 'h2h_home_wins': 4, 'odd_home': 1.95}   # Fluminense vs Botafogo
    ])
    features = ['home_goals_last5', 'away_goals_last5', 'home_form', 'away_form', 'h2h_home_wins']
    probs = model.predict_proba(test_data[features])[:, 1]

    bets = []
    for i, prob in enumerate(probs):
        edge = (prob * test_data.iloc[i]['odd_home']) - 1
        if edge > 0.05:  # Só value bets com edge > 5%
            bets.append({
                "match": ["Flamengo vs Palmeiras", "Corinthians vs São Paulo", "Fluminense vs Botafogo"][i],
                "prob_home": round(prob, 3),
                "odd_home": test_data.iloc[i]['odd_home'],
                "edge": round(edge, 3),
                "suggestion": "Aposte no mandante!" if edge > 0.10 else "Value moderada"
            })
    return bets
