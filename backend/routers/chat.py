"""
routers/chat.py — POST /api/chat

Accepts multipart form data (text message + optional image).
Implements mock AI logic:
  - Keyword match against the knowledge base → return 1st-line answer
  - If text contains "broken" or other escalation triggers → flag as unresolved
    and auto-create a ticket for 2nd-line routing
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from data import (
    DEVELOPERS,
    KNOWLEDGE_BASE,
    TICKETS,
    Developer,
    Priority,
    Ticket,
    TicketStatus,
)
from routers.tickets import assign_developer, extract_keywords

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# ---------------------------------------------------------------------------
# Escalation trigger words — any of these force 2nd-line routing
# ---------------------------------------------------------------------------

ESCALATION_TRIGGERS = {
    "broken",
    "crash",
    "crashing",
    "down",
    "outage",
    "critical",
    "urgent",
    "production",
    "cannot login",
    "can't login",
    "not working",
    "fails",
    "failed",
    "failure",
}


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class ChatResponse(BaseModel):
    resolved: bool
    ai_response: str
    ticket_id: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_priority(text: str) -> Priority:
    """Derive ticket priority from text keywords."""
    lower = text.lower()
    if any(w in lower for w in ("p1", "critical", "outage", "production down")):
        return Priority.P1
    if any(w in lower for w in ("p2", "urgent", "crash", "crashing")):
        return Priority.P2
    if any(w in lower for w in ("p3", "broken", "failed", "error")):
        return Priority.P3
    return Priority.P4


def _search_knowledge_base(text: str) -> Optional[str]:
    """Return the best-matching knowledge-base article for the query."""
    lower = text.lower()
    best_match: Optional[str] = None
    best_score = 0

    for article in KNOWLEDGE_BASE:
        score = sum(1 for kw in article["keywords"] if kw in lower)
        if score > best_score:
            best_score = score
            best_match = article["content"]

    return best_match if best_score > 0 else None


def _is_escalation(text: str) -> bool:
    """Return True if the message should bypass 1st-line and escalate immediately."""
    lower = text.lower()
    return any(trigger in lower for trigger in ESCALATION_TRIGGERS)


def _create_ticket(text: str, has_image: bool) -> Ticket:
    """Create and store a new escalated ticket."""
    priority = _detect_priority(text)
    keywords = extract_keywords(text)

    # Truncate long descriptions for the ticket title
    title = text[:80] + ("..." if len(text) > 80 else "")

    ticket = Ticket(
        title=title,
        description=text,
        priority=priority,
        status=TicketStatus.ESCALATED,
        image_attached=has_image,
        keywords=keywords,
    )

    # Attempt skill-based assignment
    developer = assign_developer(ticket, DEVELOPERS)
    if developer:
        ticket.assigned_to = developer.name
        developer.current_load += 1

    TICKETS[ticket.id] = ticket
    logger.info("Ticket %s created and assigned to %s", ticket.id, ticket.assigned_to)
    return ticket


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatResponse)
async def chat(
    message: str = Form(..., description="The user's support message"),
    image: Optional[UploadFile] = File(None, description="Optional screenshot"),
) -> ChatResponse:
    """
    1st-line AI support endpoint.

    - Searches the knowledge base for a matching answer.
    - If the message contains escalation keywords, it skips 1st-line
      and creates an escalated ticket assigned to the best-matching developer.
    - Returns whether the issue was resolved, the AI response, and ticket details.
    """
    if not message or not message.strip():
        raise HTTPException(status_code=422, detail="Message must not be empty.")

    has_image = image is not None and image.filename != ""

    # Validate image MIME type if provided
    if has_image and image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Uploaded file must be an image.")

    # -----------------------------------------------------------------------
    # Decision tree
    # -----------------------------------------------------------------------
    if _is_escalation(message):
        # Escalate immediately — skip 1st-line resolution
        ticket = _create_ticket(message, has_image)
        image_note = " I've also noted that you attached a screenshot." if has_image else ""

        return ChatResponse(
            resolved=False,
            ai_response=(
                f"⚠️ This issue has been flagged as high-priority and escalated to our 2nd-line team.{image_note} "
                f"Ticket **#{ticket.id[:8]}** has been created with priority **{ticket.priority.value}** "
                f"and assigned to **{ticket.assigned_to or 'Unassigned'}**. "
                "You will receive an update shortly."
            ),
            ticket_id=ticket.id,
            assigned_to=ticket.assigned_to,
            priority=ticket.priority.value,
        )

    # Attempt 1st-line resolution via knowledge base
    kb_answer = _search_knowledge_base(message)

    if kb_answer:
        image_note = " I can also see you've attached a screenshot for reference." if has_image else ""
        return ChatResponse(
            resolved=True,
            ai_response=(
                f"I found relevant information in our knowledge base:{image_note}\n\n"
                f"{kb_answer}\n\n"
                "Does this resolve your issue? If not, reply with more details and I'll escalate to our team."
            ),
        )

    # No KB match and no escalation trigger — create a ticket anyway for tracking
    ticket = _create_ticket(message, has_image)
    return ChatResponse(
        resolved=False,
        ai_response=(
            "I wasn't able to find an immediate answer in our knowledge base. "
            f"I've created ticket **#{ticket.id[:8]}** and assigned it to **{ticket.assigned_to or 'the team'}** "
            f"(priority **{ticket.priority.value}**). "
            "Someone will follow up with you soon."
        ),
        ticket_id=ticket.id,
        assigned_to=ticket.assigned_to,
        priority=ticket.priority.value,
    )
