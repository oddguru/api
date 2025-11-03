from fastapi import APIRouter
import joblib
import pandas as pd

router = APIRouter()
model = joblib.load("model.pkl")

@router.post("/predict")
def predict_match(data: dict):
    # Exemplo de entrada
    df = pd.DataFrame([data])
    prob = model.predict_proba(df)[0][1]
    edge = (prob * data['odd_home']) - 1
    return {
        "match": data['match'],
        "prob_home": round(prob, 3),
        "odd_home": data['odd_home'],
        "edge": round(edge, 3),
        "suggestion": "Aposte no mandante!" if edge > 0.05 else "Sem value"
    }
