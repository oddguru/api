from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict
import datetime
import json
import os
import atexit

app = FastAPI(title="OddGuru MVP")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === HISTÓRICO PERSISTENTE ===
HISTORY_FILE = "app/history.json"
try:
    with open(HISTORY_FILE, "r") as f:
        content = f.read().strip()
        HISTORY = json.loads(content) if content else []
except:
    HISTORY = []

# === JOGOS DA RODADA 33 — HOJE 09/11/2025 ===
JOGOS_HOJE = [
    {"home": "Corinthians", "away": "Ceará SC", "odd_home": 1.67, "status": "09/11 16:00"},
    {"home": "Cruzeiro", "away": "Fluminense", "odd_home": 1.88, "status": "09/11 16:00"},
    {"home": "EC Vitória", "away": "Botafogo", "odd_home": 3.30, "status": "09/11 16:00"},
    {"home": "Flamengo", "away": "Santos", "odd_home": 1.33, "status": "09/11 18:30"},
    {"home": "Mirassol", "away": "Palmeiras", "odd_home": 4.10, "status": "09/11 20:30"},
    {"home": "Fortaleza", "away": "Grêmio", "odd_home": 2.10, "status": "09/11 20:30"},
]

# === TABELA ATUALIZADA 09/11/2025 (ANTES DOS JOGOS) ===
TABELA = {
    "Palmeiras": 1, "Flamengo": 2, "Cruzeiro": 3, "Mirassol": 4, "Bahia": 5,
    "Botafogo": 6, "Fluminense": 7, "São Paulo": 8, "Atlético-MG": 9, "Vasco da Gama": 10,
    "Bragantino": 11, "Corinthians": 12, "Ceará SC": 13, "Grêmio": 14, "Internacional": 15,
    "EC Vitória": 16, "Santos": 17, "Juventude": 18, "Fortaleza": 19, "Sport Recife": 20
}

# === API: VALUE BETS COM EXPLICAÇÃO ===
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

        # === POR QUÊ PERSONALIZADO ===
        why = ""
        if home == "Mirassol" and away == "Palmeiras":
            why = "4º recebe o 1º • Mirassol 4 vitórias seguidas • Palmeiras poupou titulares • Média 2.8 gols em casa"
        elif home == "Fortaleza" and away == "Grêmio":
            why = "Fortaleza invicto em casa há 6 jogos • Grêmio sem 3 titulares • Castelão lotado"
        elif home == "EC Vitória" and away == "Botafogo":
            why = "16º em casa vs líder cansado • Botafogo jogou Libertadores quarta • Vitória venceu 2 dos últimos 3 em casa"
        elif home == "Cruzeiro" and away == "Fluminense":
            why = "3º invicto há 8 jogos • Fluminense com 3 desfalques • Cruzeiro 80% vitória em casa"
        elif home == "Corinthians" and away == "Ceará SC":
            why = "Corinthians venceu 3 dos últimos 4 • Ceará perdeu 5 dos últimos 7 fora • Neo Química lotada"
        elif home == "Flamengo" and away == "Santos":
            why = "Flamengo 2º colocado • Santos 17º e sem 4 titulares • Maracanã lotado"
        else:
            why = "Modelo OddGURU detectou valor estatístico acima de 15%"

        # === FILTRO DE VALUE BET ===
        if edge >= 0.15 and odd_home <= 4.50:
            value_bets.append({
                "match": f"{home} vs {away}",
                "status": jogo["status"],
                "odd_home": odd_home,
                "edge": round(edge, 3),
                "suggestion": "APOSTE NO MANDANTE!",
                "why": why
            })

    return {
        "value_bets": value_bets or [{"message": "Nenhuma value bet no momento. Aguarde!"}],
        "total_games": len(JOGOS_HOJE),
        "model": "OddGURU 2025"
    }

# === REGISTRAR RESULTADO ===
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
        return {"message": "Nenhuma aposta registrada."}
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

# === SALVAR AO ENCERRAR ===
def save_history():
    if HISTORY:
        with open(HISTORY_FILE, "w") as f:
            json.dump(HISTORY, f, indent=2)
atexit.register(save_history)

# === SERVIR FRONTEND ===
app.mount("/", StaticFiles(directory="public", html=True), name="static")
