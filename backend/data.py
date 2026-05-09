"""
data.py — In-memory data store for the AI Helpdesk PoC.

Contains:
- Mock knowledge base (GitHub documentation snippets)
- Mock developer profiles with skill tags
- In-memory ticket store with Pydantic models
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


# ---------------------------------------------------------------------------
# SLA targets (response time in hours by priority)
# ---------------------------------------------------------------------------

SLA_TARGETS: dict[str, int] = {
    Priority.P1: 1,
    Priority.P2: 4,
    Priority.P3: 8,
    Priority.P4: 24,
}


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class Ticket(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    priority: Priority = Priority.P3
    status: TicketStatus = TicketStatus.OPEN
    assigned_to: Optional[str] = None          # developer name
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    image_attached: bool = False
    ai_response: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)


class Developer(BaseModel):
    id: str
    name: str
    email: str
    skills: list[str]
    current_load: int = 0                      # number of tickets assigned


# ---------------------------------------------------------------------------
# Mock Knowledge Base — GitHub documentation snippets
# ---------------------------------------------------------------------------

KNOWLEDGE_BASE: list[dict] = [
    {
        "topic": "Authentication",
        "keywords": ["auth", "login", "token", "jwt", "oauth", "session", "password", "access denied"],
        "content": (
            "**Authentication Guide**: Tokens expire after 24 hours. "
            "Use `POST /api/auth/refresh` with a valid refresh token to obtain a new access token. "
            "Ensure the `Authorization: Bearer <token>` header is included in every protected request. "
            "For OAuth flows, redirect users to `/oauth/github` and handle the callback at `/oauth/callback`."
        ),
    },
    {
        "topic": "Deployment",
        "keywords": ["deploy", "deployment", "ci", "cd", "pipeline", "docker", "kubernetes", "crash", "down"],
        "content": (
            "**Deployment Guide**: Use `docker compose up -d` for local development. "
            "Production deployments are managed via GitHub Actions (`.github/workflows/deploy.yml`). "
            "Rolling deploys are enabled—zero downtime is expected. "
            "Health-check endpoint: `GET /healthz`. "
            "Rollback with `kubectl rollout undo deployment/app`."
        ),
    },
    {
        "topic": "Database",
        "keywords": ["database", "db", "sql", "query", "migration", "schema", "postgres", "slow", "timeout"],
        "content": (
            "**Database Guide**: Run migrations with `alembic upgrade head`. "
            "Connection pool size is set to 20; increase `DB_POOL_SIZE` env var if you see timeout errors. "
            "Never run raw SQL—use the ORM layer. "
            "For slow queries, check `pg_stat_statements` and add indexes via a new migration file."
        ),
    },
    {
        "topic": "Frontend",
        "keywords": ["ui", "frontend", "react", "next", "css", "component", "broken", "render", "display"],
        "content": (
            "**Frontend Guide**: The app uses Next.js 14 with the App Router. "
            "Run locally with `npm run dev`. "
            "Component library: shadcn/ui. "
            "State management: Zustand. "
            "If a page is blank, check browser console for hydration errors and ensure Server/Client component boundaries are correct."
        ),
    },
    {
        "topic": "API",
        "keywords": ["api", "endpoint", "rest", "request", "response", "cors", "error", "500", "404"],
        "content": (
            "**API Guide**: Base URL is `https://api.example.com/v1`. "
            "All responses follow `{ data, error, meta }` envelope format. "
            "Rate limit: 100 req/min per API key. "
            "For CORS issues, ensure your origin is whitelisted in the gateway config. "
            "Error codes: 401 = Unauthorized, 403 = Forbidden, 429 = Rate Limited."
        ),
    },
    {
        "topic": "Monitoring",
        "keywords": ["monitor", "alert", "log", "metric", "grafana", "pagerduty", "incident", "outage"],
        "content": (
            "**Monitoring Guide**: Logs are shipped to Datadog. "
            "Grafana dashboards are at `https://grafana.internal`. "
            "PagerDuty handles P1/P2 escalations automatically. "
            "To silence an alert: `pd-cli silence <alert-id> --duration 1h`. "
            "Runbooks are in the `/runbooks` folder of the ops repo."
        ),
    },
]


# ---------------------------------------------------------------------------
# Mock Developer Profiles
# ---------------------------------------------------------------------------

DEVELOPERS: list[Developer] = [
    Developer(
        id="dev-001",
        name="Alice Chen",
        email="alice@company.com",
        skills=["auth", "oauth", "jwt", "security", "login", "token", "session"],
    ),
    Developer(
        id="dev-002",
        name="Bob Patel",
        email="bob@company.com",
        skills=["database", "postgres", "sql", "migration", "query", "schema", "db"],
    ),
    Developer(
        id="dev-003",
        name="Carol Smith",
        email="carol@company.com",
        skills=["deployment", "docker", "kubernetes", "ci", "cd", "pipeline", "devops"],
    ),
    Developer(
        id="dev-004",
        name="David Kim",
        email="david@company.com",
        skills=["frontend", "react", "next", "css", "ui", "component", "render"],
    ),
    Developer(
        id="dev-005",
        name="Eva Rodriguez",
        email="eva@company.com",
        skills=["api", "rest", "endpoint", "cors", "integration", "microservices"],
    ),
    Developer(
        id="dev-006",
        name="Frank Obi",
        email="frank@company.com",
        skills=["monitoring", "grafana", "alert", "log", "incident", "pagerduty", "outage"],
    ),
]


# ---------------------------------------------------------------------------
# In-Memory Ticket Store
# ---------------------------------------------------------------------------

# Populated with some seed tickets so the SLA dashboard has data from the start.
def _make_seed_tickets() -> dict[str, Ticket]:
    now = datetime.now(timezone.utc)
    tickets: list[Ticket] = [
        Ticket(
            id="ticket-seed-001",
            title="Production login service returning 401",
            description="All users are unable to authenticate. JWT validation failing after key rotation.",
            priority=Priority.P1,
            status=TicketStatus.IN_PROGRESS,
            assigned_to="Alice Chen",
            created_at=now - timedelta(minutes=30),
            keywords=["auth", "jwt", "login"],
        ),
        Ticket(
            id="ticket-seed-002",
            title="Database migration failed on staging",
            description="Alembic migration head is throwing IntegrityError on the users table.",
            priority=Priority.P2,
            status=TicketStatus.OPEN,
            assigned_to="Bob Patel",
            created_at=now - timedelta(hours=2),
            keywords=["database", "migration", "sql"],
        ),
        Ticket(
            id="ticket-seed-003",
            title="CI/CD pipeline stuck on build step",
            description="GitHub Actions workflow has been pending for 45 minutes. Docker build appears to be hung.",
            priority=Priority.P2,
            status=TicketStatus.ESCALATED,
            assigned_to="Carol Smith",
            created_at=now - timedelta(hours=5),
            keywords=["deployment", "docker", "ci"],
        ),
        Ticket(
            id="ticket-seed-004",
            title="Dashboard charts not rendering",
            description="The analytics dashboard shows blank panels in Safari 17.",
            priority=Priority.P3,
            status=TicketStatus.OPEN,
            assigned_to="David Kim",
            created_at=now - timedelta(hours=3),
            keywords=["frontend", "react", "render"],
        ),
        Ticket(
            id="ticket-seed-005",
            title="CORS error on mobile API calls",
            description="iOS app receiving CORS rejection when calling /api/v1/users.",
            priority=Priority.P3,
            status=TicketStatus.RESOLVED,
            assigned_to="Eva Rodriguez",
            created_at=now - timedelta(hours=6),
            resolved_at=now - timedelta(hours=4),
            keywords=["api", "cors", "endpoint"],
        ),
        Ticket(
            id="ticket-seed-006",
            title="Grafana alert spam — disk usage",
            description="Non-critical disk usage alerts firing every 5 minutes. Needs silencing rule.",
            priority=Priority.P4,
            status=TicketStatus.RESOLVED,
            assigned_to="Frank Obi",
            created_at=now - timedelta(hours=10),
            resolved_at=now - timedelta(hours=8),
            keywords=["monitoring", "alert", "grafana"],
        ),
    ]
    return {t.id: t for t in tickets}


# The single source of truth for tickets during the server lifetime.
TICKETS: dict[str, Ticket] = _make_seed_tickets()
