from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="OddGuru PRO", version="3.0")

# ========================
# CORS
# ========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# SERVIR ESTÁTICOS
# ========================
app.mount("/public", StaticFiles(directory="public"), name="public")

# ========================
# ROTA: /env
# ========================
@app.get("/env")
async def get_env():
    return {
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY")
    }

# ========================
# ROTA: / (index.html)
# ========================
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    try:
        with open("public/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>index.html não encontrado em /public</h1>", status_code=404)

# ========================
# ROTA: /dashboard
# ========================
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    try:
        with open("public/dashboard.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>dashboard.html não encontrado em /public</h1>", status_code=404)

# ========================
# HEALTH
# ========================
@app.get("/health")
async def health():
    return {"status": "online", "service": "OddGuru PRO"}

# 3 INDEX

@app.get("/api/teaser")
async def get_teaser_bets():
    try:
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        response = supabase.table('value_bets')\
            .select('*')\
            .eq('active', True)\
            .order('edge', descending=True)\
            .limit(3)\
            .execute()
        
        return {"bets": response.data}
    except Exception as e:
        return {"bets": [], "error": str(e)}
