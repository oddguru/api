import requests
from fastapi import APIRouter

router = APIRouter()
API_TOKEN = "69a4062b62f0434d966d5aad2e78a1df"
HEADERS = {"X-Auth-Token": API_TOKEN}

@router.get("/live-odds")
def get_live_odds():
    url = "https://api.football-data.org/v4/competitions/BSA/matches"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return {"error": "API offline ou limite atingido"}

    matches = response.json().get("matches", [])
    odds_data = []
    for match in matches[:5]:  # 5 jogos
        home = match["homeTeam"]["shortName"]
        away = match["awayTeam"]["shortName"]
        odds = match.get("odds", {})
        odd_home = odds.get("homeWin", 0)
        if odd_home > 0:
            odds_data.append({
                "match": f"{home} vs {away}",
                "odd_home": round(odd_home, 2)
            })
    return odds_data
