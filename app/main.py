from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.predict import router as predict_router

app = FastAPI(title="OddGuru API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict_router, prefix="/api")

@app.get("/")
def home():
    return {"message": "OddGuru IA rodando com XGBoost!"}

# Teste rápido
@app.get("/api/test")
def test():
    return {
        "match": "Flamengo vs Palmeiras",
        "odd_home": 1.85,
        "prob_home": 0.682,
        "edge": 0.123
    }
