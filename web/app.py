"""Auto-Pipe — FastAPI Backend (JSON API + SSE)"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Auto-Pipe", docs_url="/api/docs")

# CORS for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3100"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
from web.routes.pages import router as util_router
from web.routes.bootstrap_api import router as bootstrap_router
from web.routes.pipeline_api import router as pipeline_router

app.include_router(util_router)
app.include_router(bootstrap_router, prefix="/api/bootstrap")
app.include_router(pipeline_router, prefix="/api/pipeline")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
