import uvicorn
import firebase_admin
from firebase_admin import credentials
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Local imports
from . import auth, api_routes
from .database import engine, Base
from .excel_updater import run_seeding
from .file_watcher import start_watcher_in_thread


# --- PATHS ---
BASE_DIR = pathlib.Path(__file__).resolve().parent
SDK_PATH = BASE_DIR / "firebase-sdk.json"
FRONTEND_DIST_DIR = BASE_DIR / "dist"   # ⚙️ Vite output folder


# --- FASTAPI LIFESPAN (Startup & Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Application starting up...")
    Base.metadata.create_all(bind=engine)
    run_seeding()
    start_watcher_in_thread()
    yield
    print("🛑 Application shutting down...")


# --- FIREBASE INITIALIZATION ---
try:
    cred = credentials.Certificate(SDK_PATH)
    firebase_admin.initialize_app(cred)
    print("✅ Firebase initialized successfully.")
except FileNotFoundError:
    print(f"❌ ERROR: Firebase SDK not found at {SDK_PATH}")
    exit()


# --- FASTAPI APP INSTANCE ---
app = FastAPI(
    title="NeoCart API",
    description="Full-stack FastAPI + React (Vite) setup",
    version="1.0.0",
    lifespan=lifespan
)


# --- CORS ---
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- ROUTERS ---
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(api_routes.router, prefix="/api", tags=["API"])


# --- SERVE FRONTEND (Vite's dist folder) ---
if FRONTEND_DIST_DIR.exists():
    print(f"📦 Serving Vite build from: {FRONTEND_DIST_DIR}")
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react(request: Request, full_path: str):
        index_file = FRONTEND_DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "index.html not found"}
else:
    print("⚠️ Dist folder not found! Run `npm run build` in frontend first.")


@app.get("/")
async def root():
    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "NeoCart backend is running!"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
