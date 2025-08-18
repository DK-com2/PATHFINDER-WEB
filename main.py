from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from api.auth import router as auth_router
from api.database import router as database_router
from api.map_data import router as map_data_router
from api.timeline.upload import router as timeline_upload_router
from api.timeline.fast_upload import router as timeline_fast_upload_router
from api.developer.routes import router as developer_router
from api.developer.optimized_routes import router as optimized_developer_router
from api.developer.simple_export import router as simple_export_router

load_dotenv()

app = FastAPI(
    title="Pathfinder Web",
    description="Timeline tracking and authentication system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
app.include_router(database_router, prefix="/api/timeline", tags=["database"])
app.include_router(map_data_router, prefix="/api/map", tags=["map-data"])
app.include_router(timeline_upload_router, prefix="/api/timeline", tags=["timeline-upload"])
app.include_router(timeline_fast_upload_router, prefix="/api/timeline", tags=["timeline-fast-upload"])
app.include_router(developer_router, prefix="/api/developer", tags=["developer-tools"])
app.include_router(optimized_developer_router, prefix="/api/developer", tags=["optimized-tools"])
app.include_router(simple_export_router, prefix="/api/developer/simple_export", tags=["simple-export"])

@app.get("/")
async def serve_spa():
    return FileResponse("static/index.html")

@app.get("/{full_path:path}")
async def serve_spa_routes(full_path: str):
    if full_path.startswith("api/"):
        return {"detail": "API endpoint not found"}
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)