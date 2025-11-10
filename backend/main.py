import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import firebase_admin
from firebase_admin import credentials
from . import api_routes, auth, database, excel_updater, file_watcher

app = FastAPI()

# -----------------------------------------------------
# ✅ Firebase Initialization (Render-safe environment)
# -----------------------------------------------------
firebase_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

if firebase_json:
    try:
        # Convert JSON string to dict
        firebase_creds = json.loads(firebase_json)

        # Write temporary Firebase file (Render-safe)
        temp_path = "/tmp/firebase.json"
        with open(temp_path, "w") as f:
            json.dump(firebase_creds, f)

        # Initialize Firebase using temporary file
        cred = credentials.Certificate(temp_path)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized successfully on Render.")
    except Exception as e:
        print("❌ Firebase initialization failed:", e)
else:
    print("⚠️ GOOGLE_APPLICATION_CREDENTIALS_JSON not found in environment variables.")

# -----------------------------------------------------
# ✅ CORS Setup
# -----------------------------------------------------
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------
# ✅ Include Routes
# -----------------------------------------------------
app.include_router(auth.router)
app.include_router(api_routes.router)

# -----------------------------------------------------
# ✅ Database Initialization
# -----------------------------------------------------
@app.on_event("startup")
async def startup_event():
    print("🚀 Application starting up...")
    database.Base.metadata.create_all(bind=database.engine)
    print("✅ Database tables ensured.")

    # Run Excel updater once on startup
    try:
        print("📥 Running Excel data sync...")
        excel_updater.sync_excel_with_database()
        print("✅ Excel data synced successfully.")
    except Exception as e:
        print("⚠️ Excel sync failed:", e)

    # Start watching Excel changes
    try:
        file_watcher.start_watcher()
        print("👀 Excel watcher started successfully.")
    except Exception as e:
        print("⚠️ File watcher failed to start:", e)

# -----------------------------------------------------
# ✅ Serve React Build (dist folder)
# -----------------------------------------------------
# Assuming React build folder is inside backend/dist
frontend_dist_path = os.path.join(os.path.dirname(__file__), "dist")

if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="static")

    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        return FileResponse(os.path.join(frontend_dist_path, "index.html"))
    print("📦 React frontend served from:", frontend_dist_path)
else:
    print("⚠️ React build folder not found. Please run `npm run build` in frontend.")

# -----------------------------------------------------
# ✅ Root Endpoint
# -----------------------------------------------------
@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "NeoCart backend running successfully 🚀"}


# -----------------------------------------------------
# ✅ Run Server (for local testing)
# -----------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
