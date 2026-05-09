"""
main.py — FastAPI application entry point.

Registers all routers and applies CORS middleware so the
Next.js frontend (localhost:3000) can communicate freely.

Environment variables are loaded from .env via python-dotenv
BEFORE any other module resolves os.getenv().
NODE_ENV is the primary environment identifier per project spec.
"""

# python-dotenv must be called before any other import that reads os.getenv().
from dotenv import load_dotenv
load_dotenv()  # reads backend/.env into os.environ

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, sla, tickets

_NODE_ENV = os.getenv("NODE_ENV", "development")

logging.basicConfig(
    level=logging.DEBUG if _NODE_ENV != "production" else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)
logger.info("Starting AI Helpdesk API | NODE_ENV=%s", _NODE_ENV)

app = FastAPI(
    title="AI Helpdesk API",
    version="0.2.0",
    description=(
        "AI-driven ticket management helpdesk powered by HuggingFace LLaVA. "
        "Provides 1st-line AI chat, intelligent 2nd-line routing, and SLA metrics."
    ),
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server and any local origin during hackathon
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(chat.router)
app.include_router(tickets.router)
app.include_router(sla.router)


# ---------------------------------------------------------------------------
# Health check — surfaces environment info for diagnostics
# ---------------------------------------------------------------------------
@app.get("/", tags=["health"])
def health_check():
    hf_key_set = bool(os.getenv("HUGGINGFACE_API_KEY", "").strip())
    return {
        "status": "ok",
        "message": "AI Helpdesk API is running",
        "node_env": _NODE_ENV,
        "ai_provider": "huggingface/llava-1.5-7b-hf",
        "hf_key_configured": hf_key_set,
    }
