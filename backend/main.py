import uvicorn
import firebase_admin
from firebase_admin import credentials
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles # Frontend ke liye
from fastapi.responses import FileResponse    # Frontend ke liye
import os # Path join karne ke liye

# Local modules
from . import auth, api_routes 
from .database import engine, Base

# --- Paths ---
# Yeh 'backend' folder ka poora path pata karega
BASE_DIR = pathlib.Path(__file__).resolve().parent 
SDK_PATH = BASE_DIR / "firebase-sdk.json"

# --- FastAPI Lifespan Event ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI app.
    """
    # On Startup
    print("Application startup...")
    print("Creating database tables if they don't exist...")
    Base.metadata.create_all(bind=engine) 
    yield
    # On Shutdown
    print("Application shutdown...")


# --- Firebase Admin SDK Initialization ---
try:
    # SDK_PATH ab poore path ka istemal kar raha hai
    cred = credentials.Certificate(SDK_PATH) 
    firebase_admin.initialize_app(cred)
except FileNotFoundError:
    print(f"FATAL ERROR: '{SDK_PATH}' not found. Server cannot start.")
    exit()

# --- App Definition ---
app = FastAPI(
    title="NeoCart API",
    description="Backend API for the NeoCart e-commerce platform.",
    version="1.0.0",
    lifespan=lifespan 
)

# --- API Routers (Pehle) ---
# API routes hamesha static files se *PEHLE* hone chahiye
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(api_routes.router, prefix="/api") # All other routes


# --- React Frontend (Baad mein) ---

# --- YAHAN FIX KIYA GAYA HAI ---
# BASE_DIR ka istemal karke 'dist/assets' ka poora path banaya
assets_path = os.path.join(BASE_DIR, "dist", "assets")

# Check karo ki 'dist/assets' folder hai ya nahi
if not os.path.exists(assets_path):
    print(f"WARNING: Directory not found at '{assets_path}'. Static files may not serve correctly.")
    # Ek dummy folder bana do taaki app crash na ho (optional)
    # os.makedirs(assets_path, exist_ok=True) 

app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
# --- FIX END ---


@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """
    Serve the React app's index.html for any path not matching an API route.
    """
    # Yahan bhi BASE_DIR ka istemal kiya
    html_file_path = os.path.join(BASE_DIR, "dist", "index.html")
    
    if os.path.exists(html_file_path):
        return FileResponse(html_file_path)
    else:
        # Agar dist/index.html nahi mili toh error do
        print(f"ERROR: index.html not found at '{html_file_path}'")
        return {"error": "index.html not found. Make sure you have run 'npm run build' and moved the 'dist' folder to the 'backend' directory."}

# --- Run the app ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)