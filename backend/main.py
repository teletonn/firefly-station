from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from .routers import auth, users, messages, bot_controls, audit, websocket, geolocation, zones, alerts, processes, analytics
from . import database

app = FastAPI(title="Светлячок LLM Admin API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"],  # React dev server and API server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
database.init_db()

# Include routers first
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["User Management"])
app.include_router(messages.router, prefix="/api/messages", tags=["Message Monitoring"])
app.include_router(bot_controls.router, prefix="/api/bot", tags=["Bot Controls"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit Logging"])
app.include_router(geolocation.router, prefix="/api/geolocation", tags=["Geolocation"])
app.include_router(zones.router, prefix="/api/zones", tags=["Zone Management"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alert Management"])
app.include_router(processes.router, prefix="/api/processes", tags=["Process Management"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(websocket.router, tags=["WebSocket"])

# Mount static files from React build (after routers to avoid conflicts)
build_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
if os.path.exists(build_dir):
    @app.get("/api/{path:path}")
    async def api_not_found():
        return {"error": "API endpoint not found"}

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        # Don't serve frontend for API routes
        if path.startswith("api/"):
            return {"error": "API endpoint not found"}
        file_path = os.path.join(build_dir, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        else:
            return FileResponse(os.path.join(build_dir, "index.html"))
else:
  @app.get("/")
  async def root():
    return {"message": "Светлячок LLM Admin API - Frontend not built yet"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)