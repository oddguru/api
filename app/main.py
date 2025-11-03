from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="OddGuru IA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "OddGuru IA rodando com XGBoost!"}

@app.get("/api/valuebets")
def value_bets():
    return [
        {
            "match": "Flamengo vs Palmeiras",
            "prob_home": 0.68,
            "odd_home": 1.85,
            "edge": 0.123,
            "suggestion": "Aposte no Flamengo!"
        }
    ]

@app.get("/docs")
def docs():
    return {"docs": "Acesse /docs para Swagger UI"}
