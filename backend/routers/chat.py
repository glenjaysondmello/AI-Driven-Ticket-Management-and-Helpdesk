"""
routers/chat.py — POST /api/chat

Accepts multipart form data (text message + optional image).
Delegates AI logic to ai_service.call_llm() which calls the
HuggingFace Inference API (llava-hf/llava-1.5-7b-hf).

Flow:
  1. Validate request.
  2. Read image bytes (if provided).
  3. Call ai_service.call_llm() → AIResult.
  4a. resolved=True  → return the LLM's answer directly.
  4b. resolved=False → extract routing tags, create & assign a ticket.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests as http_requests
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ai_service import AIResult, call_llm
from data import (
    DEVELOPERS,
    KNOWLEDGE_BASE,
    TICKETS,
    Priority,
    Ticket,
    TicketStatus,
)
from routers.tickets import assign_developer, extract_keywords

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


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
# Priority inference from routing tags
# ---------------------------------------------------------------------------

_P1_TAGS = {"outage", "production", "critical", "security"}
_P2_TAGS = {"auth", "jwt", "oauth", "login", "token", "deployment", "docker", "kubernetes", "ci", "cd"}
_P3_TAGS = {"database", "sql", "migration", "frontend", "react", "api", "cors", "endpoint"}


def _priority_from_tags(tags: list[str]) -> Priority:
    """
    Map LLM-produced skill tags to a ticket priority.
    Falls back to P4 when no tag matches a higher tier.
    """
    tag_set = set(t.strip().lower() for t in tags)
    if tag_set & _P1_TAGS:
        return Priority.P1
    if tag_set & _P2_TAGS:
        return Priority.P2
    if tag_set & _P3_TAGS:
        return Priority.P3
    return Priority.P4


# ---------------------------------------------------------------------------
# Ticket creation
# ---------------------------------------------------------------------------

def _create_ticket_from_llm(
    user_message: str,
    routing_tags: str,
    has_image: bool,
    ai_result: AIResult,
) -> Ticket:
    """
    Create, route, and persist a ticket driven by LLM routing tags.

    The routing tags produced by the LLM (e.g. "frontend, authentication")
    are split and used as the ticket's keywords so that assign_developer()
    can match them against developer skill sets.
    """
    tag_list = [t.strip().lower() for t in routing_tags.split(",") if t.strip()]

    # Fall back to extracting keywords from the raw user message when the
    # LLM provided no tags (shouldn't happen, but be defensive).
    keywords = tag_list if tag_list else extract_keywords(user_message)

    priority = _priority_from_tags(tag_list)
    title = user_message[:80] + ("..." if len(user_message) > 80 else "")

    ticket = Ticket(
        title=title,
        description=user_message,
        priority=priority,
        status=TicketStatus.ESCALATED,
        image_attached=has_image,
        ai_response=ai_result.raw_output[:500],   # store truncated LLM output
        keywords=keywords,
    )

    developer = assign_developer(ticket, DEVELOPERS)
    if developer:
        ticket.assigned_to = developer.name
        developer.current_load += 1

    TICKETS[ticket.id] = ticket
    logger.info(
        "Ticket %s created | priority=%s | tags=%s | assigned_to=%s",
        ticket.id[:8],
        ticket.priority.value,
        tag_list,
        ticket.assigned_to,
    )
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
    1st-line AI support endpoint powered by HuggingFace LLaVA.

    Accepts a text message and an optional image screenshot.
    Returns a resolved flag, AI response, and (if escalated) ticket details.
    """
    if not message or not message.strip():
        raise HTTPException(status_code=422, detail="Message must not be empty.")

    has_image = image is not None and image.filename not in (None, "")

    # Validate image MIME type
    if has_image and image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Uploaded file must be an image.")

    # Read image bytes once — UploadFile is a stream that can only be read once
    image_bytes: Optional[bytes] = None
    image_mime: str = "image/png"
    if has_image:
        image_bytes = await image.read()
        image_mime = image.content_type or "image/png"

    # -----------------------------------------------------------------------
    # Call the LLM (ai_service handles prompt, API, and JSON extraction)
    # -----------------------------------------------------------------------
    try:
        result: AIResult = call_llm(
            user_message=message,
            knowledge_base=KNOWLEDGE_BASE,
            image_bytes=image_bytes,
            image_mime_type=image_mime,
        )
    except EnvironmentError as exc:
        # Missing API key — surface a clear 503 so the frontend can guide the user
        logger.error("AI service misconfiguration: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except http_requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 0
        logger.error("HuggingFace API error %s: %s", status_code, exc)

        if status_code == 503:
            detail = (
                "The AI model is currently loading on HuggingFace servers "
                "(cold start). Please retry in 20–60 seconds."
            )
        elif status_code == 401:
            detail = "Invalid HUGGINGFACE_API_KEY. Check your .env file."
        else:
            detail = f"HuggingFace API returned HTTP {status_code}. Please retry."

        raise HTTPException(status_code=502, detail=detail) from exc
    except Exception as exc:
        logger.exception("Unexpected error calling AI service: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your request.",
        ) from exc

    # -----------------------------------------------------------------------
    # Route based on LLM decision
    # -----------------------------------------------------------------------
    image_note = " I can see you've attached a screenshot for context." if has_image else ""

    if result.resolved:
        # LLM answered — return directly, no ticket needed
        return ChatResponse(
            resolved=True,
            ai_response=f"{result.response_or_routing_tags}{image_note}",
        )

    # LLM could not resolve — create a ticket from the routing tags
    ticket = _create_ticket_from_llm(
        user_message=message,
        routing_tags=result.response_or_routing_tags,
        has_image=has_image,
        ai_result=result,
    )

    return ChatResponse(
        resolved=False,
        ai_response=(
            f"⚠️ I was unable to resolve this from the knowledge base.{image_note} "
            f"I've escalated ticket **#{ticket.id[:8]}** with priority **{ticket.priority.value}** "
            f"to **{ticket.assigned_to or 'the team'}** based on the required skills "
            f"(*{result.response_or_routing_tags}*). You'll hear back shortly."
        ),
        ticket_id=ticket.id,
        assigned_to=ticket.assigned_to,
        priority=ticket.priority.value,
    )
