import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from supabase import create_client

# === CONFIGURAÇÃO DO APP ===
app = FastAPI()

# Monta pasta public (index.html, dashboard.html, etc)
app.mount("/public", StaticFiles(directory="public"), name="public")

# CORS (permite tudo — ajuste depois se quiser segurança)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === VARIÁVEIS DO AMBIENTE (RENDER) ===
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# === ROTA: / (INDEX) ===
@app.get("/", response_class=HTMLResponse)
async def get_index():
    return FileResponse("public/index.html")

# === ROTA: /dashboard ===
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    return FileResponse("public/dashboard.html")

# === ROTA: /env (SEGURA, SÓ LEITURA) ===
@app.get("/env")
async def get_env():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return JSONResponse({"error": "Configuração ausente"}, status_code=500)
    return {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY
    }

# === ROTA: /api/teaser (3 MELHORES APOSTAS) ===
@app.get("/api/teaser")
async def get_teaser_bets():
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("ERRO: SUPABASE_URL ou SUPABASE_KEY não configurados")
            return {"bets": [], "error": "Supabase não configurado"}

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = supabase.table('value_bets')\
            .select('*')\
            .eq('active', True)\
            .order('edge', descending=True)\
            .limit(3)\
            .execute()
        
        print(f"Teaser: {len(response.data)} apostas encontradas")
        return {"bets": response.data}
    except Exception as e:
        print("Erro /api/teaser:", str(e))
        return {"bets": [], "error": str(e)}

# === ROTA: /api/telegram (RECEBE DO SUPABASE TRIGGER) ===
@app.post("/api/telegram")
async def send_to_telegram(request: Request):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERRO: Telegram não configurado (TOKEN ou CHAT_ID ausente)")
        return {"status": "error", "msg": "Telegram não configurado"}

    try:
        data = await request.json()
        
        message = (
            f"<b>{data['match']}</b>\n\n"
            f"<b>{data['selection']}</b>\n"
            f"Odd: <b>{data['odd']}</b> | +{int(data['edge']*100)}%\n\n"
            f"<i>{data['why']}</i>\n\n"
            f"Aposte na {data['bookmaker']} →"
        )

        keyboard = {
            "inline_keyboard": [[
                {
                    "text": "Apostar",
                    "url": data['affiliate_link']
                }
            ]]
        }

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                print("Erro Telegram API:", response.text)

        return {"status": "sent"}
    except Exception as e:
        print("Erro no envio Telegram:", str(e))
        return {"status": "error", "msg": str(e)}

# === ROTA: /health (OPCIONAL) ===
@app.get("/health")
async def health():
    return {"status": "ok", "service": "OddGuru PRO API"}
