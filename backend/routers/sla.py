"""
routers/sla.py — GET /api/sla

Computes real-time SLA metrics from the in-memory ticket store:
  - Per-priority ticket counts and resolution rates
  - Breached vs within-SLA counts
  - Average resolution time per priority
  - Summary stats for the dashboard header
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from data import SLA_TARGETS, TICKETS, Priority, Ticket, TicketStatus

router = APIRouter(prefix="/api/sla", tags=["sla"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class PrioritySLAMetric(BaseModel):
    priority: str
    target_hours: int
    total: int
    open: int
    in_progress: int
    escalated: int
    resolved: int
    breached: int                       # tickets that exceeded SLA target
    within_sla: int
    resolution_rate_pct: float          # 0-100
    avg_resolution_hours: Optional[float] = None


class SLASummary(BaseModel):
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    escalated_tickets: int
    overall_breach_rate_pct: float
    overall_resolution_rate_pct: float


class SLAResponse(BaseModel):
    generated_at: str
    summary: SLASummary
    by_priority: list[PrioritySLAMetric]
    recent_tickets: list[dict]          # last 10 for the table widget


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

from typing import Optional  # noqa: E402  (placed here for readability)


def _hours_since(dt: datetime) -> float:
    """Return elapsed hours from dt to now (UTC)."""
    now = datetime.now(timezone.utc)
    return (now - dt).total_seconds() / 3600


def _is_breached(ticket: Ticket, target_hours: int) -> bool:
    """
    A ticket is 'breached' if:
      - It is NOT resolved AND it has been open longer than the SLA target, OR
      - It IS resolved but resolution took longer than the SLA target.
    """
    if ticket.status == TicketStatus.RESOLVED and ticket.resolved_at:
        elapsed = (ticket.resolved_at - ticket.created_at).total_seconds() / 3600
        return elapsed > target_hours
    # Still open
    return _hours_since(ticket.created_at) > target_hours


def _avg_resolution_hours(tickets: list[Ticket]) -> Optional[float]:
    """Average resolution time for a list of resolved tickets, in hours."""
    resolved = [
        t for t in tickets
        if t.status == TicketStatus.RESOLVED and t.resolved_at is not None
    ]
    if not resolved:
        return None
    total = sum(
        (t.resolved_at - t.created_at).total_seconds() / 3600
        for t in resolved
    )
    return round(total / len(resolved), 2)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("", response_model=SLAResponse)
def get_sla_metrics() -> SLAResponse:
    """
    Return SLA metrics aggregated by priority (P1–P4) plus a summary.
    """
    all_tickets = list(TICKETS.values())
    by_priority: list[PrioritySLAMetric] = []

    total_breached = 0
    total_resolved = 0

    for priority in [Priority.P1, Priority.P2, Priority.P3, Priority.P4]:
        target_hours = SLA_TARGETS[priority]
        group = [t for t in all_tickets if t.priority == priority]

        counts: dict[str, int] = {
            "open": 0,
            "in_progress": 0,
            "escalated": 0,
            "resolved": 0,
        }
        for t in group:
            counts[t.status.value] = counts.get(t.status.value, 0) + 1

        breached = sum(1 for t in group if _is_breached(t, target_hours))
        within_sla = len(group) - breached

        resolved_count = counts["resolved"]
        resolution_rate = (resolved_count / len(group) * 100) if group else 0.0

        total_breached += breached
        total_resolved += resolved_count

        by_priority.append(
            PrioritySLAMetric(
                priority=priority,
                target_hours=target_hours,
                total=len(group),
                open=counts["open"],
                in_progress=counts["in_progress"],
                escalated=counts["escalated"],
                resolved=resolved_count,
                breached=breached,
                within_sla=within_sla,
                resolution_rate_pct=round(resolution_rate, 1),
                avg_resolution_hours=_avg_resolution_hours(group),
            )
        )

    total = len(all_tickets)
    total_open = sum(1 for t in all_tickets if t.status == TicketStatus.OPEN)
    total_escalated = sum(1 for t in all_tickets if t.status == TicketStatus.ESCALATED)
    breach_rate = (total_breached / total * 100) if total else 0.0
    resolution_rate = (total_resolved / total * 100) if total else 0.0

    summary = SLASummary(
        total_tickets=total,
        open_tickets=total_open,
        resolved_tickets=total_resolved,
        escalated_tickets=total_escalated,
        overall_breach_rate_pct=round(breach_rate, 1),
        overall_resolution_rate_pct=round(resolution_rate, 1),
    )

    # Recent 10 tickets for the dashboard table (newest first)
    recent = sorted(all_tickets, key=lambda t: t.created_at, reverse=True)[:10]
    recent_rows: list[dict[str, Any]] = [
        {
            "id": t.id[:8],
            "title": t.title,
            "priority": t.priority,
            "status": t.status,
            "assigned_to": t.assigned_to or "Unassigned",
            "created_at": t.created_at.isoformat(),
            "breached": _is_breached(t, SLA_TARGETS[t.priority]),
        }
        for t in recent
    ]

    return SLAResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        summary=summary,
        by_priority=by_priority,
        recent_tickets=recent_rows,
    )
