# === SUBSTITUA O /api/smart-bets POR ESSE ===
@app.get("/api/smart-bets")
def smart_bets() -> Dict:
    value_bets = []

    # POSIÇÃO NA TABELA (08/11/2025)
    tabela = {
        "Flamengo": 1, "Botafogo": 2, "Palmeiras": 3, "São Paulo": 4,
        "Internacional": 5, "Cruzeiro": 6, "Corinthians": 7, "Fortaleza": 8,
        "Vasco da Gama": 9, "Bahia": 10, "Atlético-MG": 11, "Grêmio": 12,
        "Vitória": 13, "Fluminense": 14, "Ceará": 15, "Juventude": 16,
        "Sport Recife": 17, "Bragantino": 18, "Santos": 19, "Mirassol": 20
    }

    for jogo in JOGOS_HOJE:
        home = jogo["home"]
        odd_home = jogo["odd_home"]
        
        # PROBABILIDADE REALISTA
        pos_home = tabela.get(home, 20)
        pos_away = tabela.get(jogo["away"], 20)
        
        # Mandante top 8 = +15% | Fora do G8 = -10%
        prob_home = 0.50
        if pos_home <= 8: prob_home += 0.15
        if pos_home > 12: prob_home -= 0.10
        if pos_away <= 4: prob_home -= 0.12  # Time forte fora
        
        prob_home = max(0.30, min(0.75, prob_home))  # Limite 30-75%

        edge = (prob_home * odd_home) - 1

        # FILTROS DE SEGURANÇA
        if (edge > 0.15 and  # Edge realista
            odd_home <= 2.50 and  # Não manda zebra
            pos_home <= 12):  # Só times competitivos

            value_bets.append({
                "match": f"{home} vs {jogo['away']}",
                "status": jogo["status"],
                "odd_home": odd_home,
                "edge": round(edge, 3),
                "prob": round(prob_home, 3),
                "suggestion": "APOSTE NO MANDANTE!"
            })

    return {
        "value_bets": value_bets or [{"message": "Nenhuma value bet segura hoje"}],
        "total_games": len(JOGOS_HOJE),
        "model": "Tabela + posição realista"
    }
