"""
main.py — FastAPI application entry point.

Registers all routers and applies CORS middleware so the
Next.js frontend (localhost:3000) can communicate freely.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, sla, tickets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(
    title="AI Helpdesk API",
    version="0.1.0",
    description=(
        "AI-driven ticket management helpdesk. "
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
# Health check
# ---------------------------------------------------------------------------
@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "message": "AI Helpdesk API is running"}
