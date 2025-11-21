import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from supabase import create_client

app = FastAPI(title="OddGuru PRO v12.0")

# Serve arquivos estáticos (index.html, dashboard.html, etc)
app.mount("/public", StaticFiles(directory="public"), name="public")

# CORS (permite tudo — ajuste depois se quiser mais segurança)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variáveis do Render
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

# === ROTA: /env (para o frontend pegar as chaves) ===
@app.get("/env")
async def get_env():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return JSONResponse({"error": "Configuração ausente"}, status_code=500)
    return {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY
    }

# === ROTA: /api/teaser (3 melhores apostas para a home) ===
@app.get("/api/teaser")
async def get_teaser_bets():
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return {"bets": []}

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = supabase.table('value_bets')\
            .select('*')\
            .eq('active', True)\
            .order('edge', ascending=False) \
            .limit(3)\
            .execute()
        
        return {"bets": response.data}
    except Exception as e:
        print("Erro /api/teaser:", str(e))
        return {"bets": []}

# === ROTA: /api/telegram (recebe do Supabase Trigger) ===
@app.post("/api/telegram")
async def send_to_telegram(request: Request):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
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
        keyboard = {"inline_keyboard": [[{"text": "Apostar", "url": data['affiliate_link']}]]}
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML", "reply_markup": keyboard}

        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)

        return {"status": "sent"}
    except Exception as e:
        print("Erro Telegram:", str(e))
        return {"status": "error", "msg": str(e)}

# === ROTA: /health ===
@app.get("/health")
async def health():
    return {"status": "ok"}
