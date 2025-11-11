from fastapi import FastAPI
import requests
from supabase import create_client, Client
import os
from datetime import date

app = FastAPI()

# --- CONFIGURAÇÕES ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "7dcbc0af76b1be4e91195a55f8f77010")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Liga Brasileira Série A (id=71)
LEAGUE_ID = 71
SEASON = 2024

@app.get("/update-today")
def update_today_matches():
    today = date.today().strftime("%Y-%m-%d")

    url = f"https://v3.football.api-sports.io/fixtures?league={LEAGUE_ID}&season={SEASON}&date={today}"
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    res = requests.get(url, headers=headers)
    data = res.json()

    if "response" not in data:
        return {"error": "API sem retorno válido", "data": data}

    saved = []
    for item in data["response"]:
        fixture = item["fixture"]
        teams = item["teams"]
        league = item["league"]

        match_data = {
            "fixture_id": fixture["id"],
            "date": fixture["date"],
            "league": league["name"],
            "home_team": teams["home"]["name"],
            "away_team": teams["away"]["name"],
        }

        supabase.table("matches").upsert(match_data).execute()
        saved.append(match_data)

    return {"message": f"{len(saved)} partidas salvas com sucesso.", "matches": saved}
