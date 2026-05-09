"""
routers/tickets.py — GET /api/tickets & POST /api/tickets/route

Provides:
  - List of all tickets with optional status filtering
  - Skill-based developer assignment logic (used by chat router)
  - Manual re-routing endpoint for unresolved tickets
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from data import DEVELOPERS, TICKETS, Developer, Ticket, TicketStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


# ---------------------------------------------------------------------------
# Utility: keyword extraction
# ---------------------------------------------------------------------------

# Common stop words to ignore when building keyword lists
_STOP_WORDS = {
    "the", "is", "are", "was", "were", "a", "an", "in", "on", "at", "to",
    "for", "of", "and", "or", "but", "not", "with", "my", "our", "i", "we",
    "it", "this", "that", "can", "have", "has", "from", "get", "when", "how",
    "what", "why", "where", "been", "be", "do", "does", "did", "will",
    "would", "could", "should", "just", "also", "after", "before",
}


def extract_keywords(text: str) -> list[str]:
    """
    Extract meaningful single-word tokens from text.
    Strips punctuation and removes common stop words.
    Returns lowercase unique tokens, max 20.
    """
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    return list({t for t in tokens if t not in _STOP_WORDS and len(t) > 2})[:20]


# ---------------------------------------------------------------------------
# Core routing logic
# ---------------------------------------------------------------------------

def assign_developer(ticket: Ticket, developers: list[Developer]) -> Optional[Developer]:
    """
    Match ticket keywords against developer skill tags.
    Selects the developer with the highest skill-overlap score,
    using current_load as a tiebreaker (prefer less-loaded developer).

    Returns None if no developer has any matching skill.
    """
    best_dev: Optional[Developer] = None
    best_score = -1

    for dev in developers:
        skill_set = set(dev.skills)
        keyword_set = set(ticket.keywords)
        overlap = len(skill_set & keyword_set)

        if overlap > best_score or (overlap == best_score and best_dev and dev.current_load < best_dev.current_load):
            best_score = overlap
            best_dev = dev

    return best_dev if best_score > 0 else None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TicketListResponse(BaseModel):
    tickets: list[Ticket]
    total: int


class RouteResponse(BaseModel):
    ticket_id: str
    assigned_to: Optional[str]
    status: TicketStatus
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=TicketListResponse)
def list_tickets(
    status: Optional[TicketStatus] = Query(None, description="Filter by ticket status"),
    priority: Optional[str] = Query(None, description="Filter by priority (P1-P4)"),
) -> TicketListResponse:
    """
    Return all tickets, optionally filtered by status and/or priority.
    """
    results = list(TICKETS.values())

    if status:
        results = [t for t in results if t.status == status]

    if priority:
        p = priority.upper()
        results = [t for t in results if t.priority == p]

    # Sort: open/escalated first, then by priority ascending (P1 > P2 > P3 > P4)
    priority_order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    status_order = {
        TicketStatus.ESCALATED: 0,
        TicketStatus.IN_PROGRESS: 1,
        TicketStatus.OPEN: 2,
        TicketStatus.RESOLVED: 3,
    }
    results.sort(key=lambda t: (status_order.get(t.status, 9), priority_order.get(t.priority, 9)))

    return TicketListResponse(tickets=results, total=len(results))


@router.post("/route/{ticket_id}", response_model=RouteResponse)
def route_ticket(ticket_id: str) -> RouteResponse:
    """
    Manually trigger routing for an existing unresolved ticket.
    Useful for re-assigning tickets that failed initial auto-routing.
    """
    ticket = TICKETS.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")

    if ticket.status == TicketStatus.RESOLVED:
        return RouteResponse(
            ticket_id=ticket_id,
            assigned_to=ticket.assigned_to,
            status=ticket.status,
            message="Ticket is already resolved — no routing needed.",
        )

    developer = assign_developer(ticket, DEVELOPERS)

    if developer:
        ticket.assigned_to = developer.name
        ticket.status = TicketStatus.ESCALATED
        developer.current_load += 1
        msg = f"Ticket routed to {developer.name} based on skill match."
    else:
        msg = "No matching developer found. Ticket remains unassigned."

    logger.info("route_ticket %s → %s", ticket_id, ticket.assigned_to)
    return RouteResponse(
        ticket_id=ticket_id,
        assigned_to=ticket.assigned_to,
        status=ticket.status,
        message=msg,
    )
