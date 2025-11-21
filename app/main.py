import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from supabase import create_client

app = FastAPI()

# Serve arquivos estáticos
app.mount("/public", StaticFiles(directory="public"), name="public")

# CORS
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

# /env (para o dashboard)
@app.get("/env")
async def get_env():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return JSONResponse({"error": "Supabase não configurado"}, status_code=500)
    return {"SUPABASE_URL": SUPABASE_URL, "SUPABASE_KEY": SUPABASE_KEY}

# /api/teaser (3 apostas para a home)
# === ROTA: /api/teaser (CORRIGIDA) ===
@app.get("/api/teaser")
async def get_teaser_bets():
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("ERRO: Supabase não configurado")
            return {"bets": []}

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = supabase.table('value_bets')\
            .select('*')\
            .eq('active', True)\
            .order('edge', ascending=False)  # <-- CORRIGIDO AQUI
            .limit(3)\
            .execute()
        
        print(f"Teaser: {len(response.data)} apostas encontradas")
        return {"bets": response.data}
    except Exception as e:
        print("Erro /api/teaser:", str(e))
        return {"bets": []}

# Rota raiz
@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("public/index.html")

# Dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return FileResponse("public/dashboard.html")

# Health
@app.get("/health")
async def health():
    return {"status": "ok"}
