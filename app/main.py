from flask import Flask, jsonify
import requests
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
THESPORTSDB_URL = "https://www.thesportsdb.com/api/v1/json/3/eventsday.php"
# ID do Campeonato Brasileiro Série A no TheSportsDB
LEAGUE_ID = "4424"  # Brasileirão Série A (ID oficial)
TIMEZONE = "America/Sao_Paulo"


def get_matches_by_date(date_str):
    """Busca os jogos do Brasileirão na data especificada."""
    params = {
        "d": date_str,
        "l": "Brazilian Série A"
    }
    try:
        response = requests.get(THESPORTSDB_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data or not data.get("events"):
            return None

        jogos = []
        for event in data["events"]:
            jogos.append({
                "home": event.get("strHomeTeam"),
                "away": event.get("strAwayTeam"),
                "date": event.get("dateEvent"),
                "time": event.get("strTime"),
                "status": event.get("strStatus") or "A definir",
                "home_score": event.get("intHomeScore"),
                "away_score": event.get("intAwayScore")
            })
        return jogos
    except Exception as e:
        print(f"Erro ao buscar jogos: {e}")
        return None


@app.route("/api/update-today", methods=["GET"])
def update_today():
    today = datetime.now().date()
    dates_to_try = [
        today.strftime("%Y-%m-%d"),
        (today - timedelta(days=1)).strftime("%Y-%m-%d"),
        (today + timedelta(days=1)).strftime("%Y-%m-%d")
    ]

    for date_str in dates_to_try:
        jogos = get_matches_by_date(date_str)
        if jogos:
            return jsonify({
                "status": "Jogos encontrados",
                "date": date_str,
                "matches": jogos
            })

    return jsonify({
        "status": "Sem jogos disponíveis",
        "date": today.strftime("%Y-%m-%d")
    })


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "API funcionando",
        "endpoints": {
            "/api/update-today": "Retorna os jogos do Brasileirão Série A do dia"
        }
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
