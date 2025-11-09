from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict, List
import datetime
import json
import os
import atexit

# === APP PRIMEIRO (OBRIGATÓRIO) ===
app = FastAPI(title="OddGuru MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === HISTÓRICO PERSISTENTE (DENTRO DO app/ — FUNCIONA NO RENDER) ===
HISTORY_FILE = "app/history.json"
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r") as f:
            HISTORY = json.load(f)
    except:
        HISTORY = []
else:
    HISTORY = []

# === JOGOS DA RODADA 33 (BETANO - 08/11/2025) ===
JOGOS_HOJE = [
    {"home": "Sport Recife", "away": "Atlético-MG", "odd_home": 3.55, "status": "08/11 16:00"},
    {"home": "Vasco da Gama", "away": "Juventude", "odd_home": 1.53, "status": "08/11 16:00"},
    {"home": "Internacional", "away": "Bahia", "odd_home": 2.35, "status": "08/11 18:30"},
    {"home": "São Paulo", "away": "Bragantino", "odd_home": 1.80, "status": "08/11 21:00"},
    {"home": "Corinthians", "away": "Ceará SC", "odd_home": 1.67, "status": "09/11 16:00"},
    {"home": "Cruzeiro", "away": "Fluminense", "odd_home": 1.88, "status": "09/11 16:00"},
    {"home": "EC Vitória", "away": "Botafogo", "odd_home": 3.30, "status": "09/11 16:00"},
    {"home": "Flamengo", "away": "Santos", "odd_home": 1.33, "status": "09/11 18:30"},
    {"home": "Mirassol", "away": "Palmeiras", "odd_home": 4.10, "status": "09/11 20:30"},
    {"home": "Fortaleza", "away": "Grêmio", "odd_home": 2.10, "status": "09/11 20:30"},
]

# === TABELA DE CLASSIFICAÇÃO (09/11/2025 — ANTES DA RODADA 33) ===
TABELA = {
    "Palmeiras": 1,
    "Flamengo": 2,
    "Cruzeiro": 3,
    "Mirassol": 4,
    "Bahia": 5,
    "Botafogo": 6,
    "Fluminense": 7,
    "São Paulo": 8,
    "Atlético-MG": 9,
    "Vasco da Gama": 10,
    "Bragantino": 11,
    "Corinthians": 12,
    "Ceará SC": 13,
    "Grêmio": 14,
    "Internacional": 15,
    "EC Vitória": 16,
    "Santos": 17,
    "Juventude": 18,
    "Fortaleza": 19,
    "Sport Recife": 20
}

# === API: VALUE BETS (MODELO REALISTA + FILTROS) ===
@app.get("/api/smart-bets")
def smart_bets() -> Dict:
    value_bets = []
    for jogo in JOGOS_HOJE:
        home = jogo["home"]
        away = jogo["away"]
        odd_home = jogo["odd_home"]
        pos_home = TABELA.get(home, 20)
        pos_away = TABELA.get(away, 20)
        
        prob_home = 0.50
        if pos_home <= 8: prob_home += 0.15
        if pos_home > 12: prob_home -= 0.10
        if pos_away <= 4: prob_home -= 0.12
        if pos_home <= 4: prob_home += 0.08
        prob_home = max(0.30, min(0.75, prob_home))
        
        edge = (prob_home * odd_home) - 1
        
        if (edge >= 0.15 and odd_home <= 2.50 and pos_home <= 12):
            value_bets.append({
                "match": f"{home} vs {away}",
                "status": jogo["status"],
                "odd_home": odd_home,
                "edge": round(edge, 3),
                "prob_home": round(prob_home, 3),
                "suggestion": "APOSTE NO MANDANTE!"
            })
    
    return {
        "value_bets": value_bets or [{"message": "Nenhuma value bet segura hoje. Aguarde amanhã!"}],
        "total_games": len(JOGOS_HOJE),
        "api_source": "Odds Betano (08/11/2025)",
        "model": "Tabela + filtro de segurança"
    }

# === REGISTRAR RESULTADO (SALVA NO app/history.json) ===
@app.get("/api/record-result-get")
def record_result_get(
    match: str = Query(...),
    odd: float = Query(...),
    edge: float = Query(...),
    result: str = Query(..., regex="^(win|loss)$")
):
    global HISTORY
    new_entry = {
        "match": match,
        "odd": odd,
        "edge": round(edge, 3),
        "result": result,
        "date": datetime.datetime.now().strftime("%d/%m %H:%M")
    }
    HISTORY.append(new_entry)
    
    with open(HISTORY_FILE, "w") as f:
        json.dump(HISTORY, f, indent=2)
    
    return {"status": "registrado", "total": len(HISTORY)}

# === HISTÓRICO + ROI ===
@app.get("/api/history")
def get_history():
    if not HISTORY:
        return {"message": "Nenhuma aposta registrada. Use /api/record-result-get"}
    
    wins = len([h for h in HISTORY if h["result"] == "win"])
    total = len(HISTORY)
    profit = sum((h["odd"] - 1) * 100 for h in HISTORY if h["result"] == "win") - ((total - wins) * 100)
    roi = (profit / (total * 100)) if total > 0 else 0

    return {
        "total_bets": total,
        "wins": wins,
        "losses": total - wins,
        "profit": round(profit, 2),
        "roi": f"{roi*100:.1f}%",
        "history": HISTORY[-10:]
    }

# === DEBUG ===
@app.get("/api/debug")
def debug():
    return {"status": "API viva", "historico": len(HISTORY), "arquivo": HISTORY_FILE}

# === MOSTRAR O ARQUIVO SALVO (PARA VOCÊ VER QUE TÁ LÁ!) ===
@app.get("/api/show-history-file")
def show_history_file():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            content = f.read()
        return {"file": HISTORY_FILE, "content": json.loads(content)}
    else:
        return {"error": "Arquivo history.json não encontrado"}

# === SALVAR AO ENCERRAR (SEGURANÇA EXTRA) ===
def save_history():
    if HISTORY:
        with open(HISTORY_FILE, "w") as f:
            json.dump(HISTORY, f, indent=2)
atexit.register(save_history)

# === SERVIR FRONTEND ===
app.mount("/", StaticFiles(directory="public", html=True), name="static")
