"use client";

import { useCallback, useEffect, useState } from "react";
import TopBar from "../components/TopBar";

const API_BASE = "http://localhost:8000";

/** How often to poll the SLA endpoint (ms) */
const POLL_INTERVAL = 15_000;

/** Priority colour tokens mapping to CSS variables */
const PRIORITY_COLORS = {
  P1: "var(--p1)",
  P2: "var(--p2)",
  P3: "var(--p3)",
  P4: "var(--p4)",
};

const PRIORITY_LABELS = {
  P1: "Critical",
  P2: "High",
  P3: "Medium",
  P4: "Low",
};

/** Formats ISO datetime to a short local string */
function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Animated big-number with size variant based on priority */
function PriorityCard({ metric }) {
  const color = PRIORITY_COLORS[metric.priority];
  const isP1 = metric.priority === "P1";
  const isP2 = metric.priority === "P2";
  const sizeClass = isP1 ? "" : isP2 ? "sm" : "xs";
  const resolution = metric.resolution_rate_pct ?? 0;
  const breachPct =
    metric.total > 0 ? (metric.breached / metric.total) * 100 : 0;

  return (
    <div
      className={`priority-card ${sizeClass}`}
      data-priority={metric.priority}
      style={{ "--card-color": color }}
      aria-label={`${metric.priority} ${PRIORITY_LABELS[metric.priority]} — ${metric.total} tickets`}
    >
      {/* Badge */}
      <div>
        <span className="priority-badge" style={{ color }}>
          <span aria-hidden="true">●</span>
          {metric.priority} — {PRIORITY_LABELS[metric.priority]}
        </span>
      </div>

      {/* Big number */}
      <div
        className="priority-big-number"
        aria-label={`${metric.total} total tickets`}
      >
        {metric.total}
      </div>
      <div className="priority-card-label">total tickets</div>

      {/* SLA target chip */}
      <div className="sla-target-chip" title="SLA response target">
        ⏱ {metric.target_hours}h target
      </div>

      {/* Stats */}
      <div className="priority-card-meta">
        {[
          ["Open", metric.open],
          ["In Progress", metric.in_progress],
          ["Escalated", metric.escalated],
          ["Resolved", metric.resolved],
        ].map(([label, val]) => (
          <div key={label} className="priority-card-stat">
            <span>{label}</span>
            <span>{val}</span>
          </div>
        ))}

        {/* Resolution progress bar */}
        <div className="breach-bar" title={`Resolution rate: ${resolution}%`}>
          <div
            className="breach-bar-fill"
            style={{ width: `${resolution}%` }}
            role="progressbar"
            aria-valuenow={resolution}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`${resolution}% resolved`}
          />
        </div>

        <div className="priority-card-stat" style={{ marginTop: 4 }}>
          <span>Resolution rate</span>
          <span style={{ color: resolution > 50 ? "var(--status-green)" : "var(--status-amber)" }}>
            {resolution}%
          </span>
        </div>

        {metric.breached > 0 && (
          <div className="priority-card-stat">
            <span>SLA breached</span>
            <span style={{ color: "var(--status-red)", fontWeight: 700 }}>
              {metric.breached}
            </span>
          </div>
        )}

        {metric.avg_resolution_hours != null && (
          <div className="priority-card-stat">
            <span>Avg resolution</span>
            <span>{metric.avg_resolution_hours}h</span>
          </div>
        )}
      </div>
    </div>
  );
}

/** Summary stat cell */
function SummaryCell({ label, value, variant }) {
  return (
    <div className="summary-cell">
      <span className="summary-cell-label">{label}</span>
      <span className={`summary-cell-value ${variant ?? ""}`}>{value}</span>
    </div>
  );
}

/** Status badge */
function StatusBadge({ status }) {
  const label = status?.replace("_", " ") ?? "—";
  return <span className={`badge-s ${status}`}>{label}</span>;
}

/** Priority badge */
function PBadge({ priority }) {
  return <span className={`badge-p ${priority}`}>{priority}</span>;
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchSla = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sla`, { cache: "no-store" });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const json = await res.json();
      setData(json);
      setLastUpdated(new Date().toLocaleTimeString());
      setError(null);
    } catch (err) {
      setError(err.message ?? "Failed to load SLA data");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch + polling
  useEffect(() => {
    fetchSla();
    const id = setInterval(fetchSla, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [fetchSla]);

  const summary = data?.summary;
  const byPriority = data?.by_priority ?? [];
  const recentTickets = data?.recent_tickets ?? [];

  return (
    <div className="page-shell">
      <TopBar />

      {isLoading && !data ? (
        <div className="state-message" role="status" aria-live="polite">
          <div className="spinner" aria-hidden="true" />
          &nbsp;&nbsp;Loading SLA data…
        </div>
      ) : error && !data ? (
        <div
          className="state-message"
          role="alert"
          style={{ color: "var(--status-red)" }}
        >
          ⚠ {error}
        </div>
      ) : (
        <div className="dashboard-body">
          {/* ── Header ── */}
          <div className="dashboard-header">
            <h1 className="dashboard-title">SLA Dashboard</h1>
            <div
              className="dashboard-timestamp"
              aria-live="polite"
              aria-label={`Last updated ${lastUpdated}`}
            >
              {error ? (
                <span style={{ color: "var(--status-red)" }}>
                  ⚠ Stale — {error}
                </span>
              ) : (
                `Updated ${lastUpdated} · auto-refreshes every 15s`
              )}
            </div>
          </div>

          {/* ── Summary strip ── */}
          {summary && (
            <div
              className="summary-strip"
              role="region"
              aria-label="Overview metrics"
            >
              <SummaryCell
                label="Total Tickets"
                value={summary.total_tickets}
              />
              <SummaryCell
                label="Open"
                value={summary.open_tickets}
                variant={summary.open_tickets > 0 ? "warn" : "ok"}
              />
              <SummaryCell
                label="Breach Rate"
                value={`${summary.overall_breach_rate_pct}%`}
                variant={summary.overall_breach_rate_pct > 20 ? "danger" : summary.overall_breach_rate_pct > 0 ? "warn" : "ok"}
              />
              <SummaryCell
                label="Resolved"
                value={`${summary.overall_resolution_rate_pct}%`}
                variant={summary.overall_resolution_rate_pct > 60 ? "ok" : "warn"}
              />
            </div>
          )}

          {/* ── Priority grid ── */}
          <section aria-label="Priority breakdown">
            <div className="priority-grid">
              {byPriority.map((metric) => (
                <PriorityCard key={metric.priority} metric={metric} />
              ))}
            </div>
          </section>

          {/* ── Recent tickets table ── */}
          <section className="table-section" aria-label="Recent tickets">
            <div className="table-section-header">
              <h2 className="table-section-title">Recent Tickets</h2>
              <span className="table-count" aria-label={`${recentTickets.length} tickets shown`}>
                {recentTickets.length} shown
              </span>
            </div>

            {recentTickets.length === 0 ? (
              <p
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 12,
                  color: "var(--text-dim)",
                  padding: "20px 0",
                }}
              >
                No tickets yet.
              </p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table
                  className="ticket-table"
                  aria-label="Ticket list"
                >
                  <thead>
                    <tr>
                      <th scope="col">ID</th>
                      <th scope="col">Title</th>
                      <th scope="col">Priority</th>
                      <th scope="col">Status</th>
                      <th scope="col">Assigned To</th>
                      <th scope="col">Created</th>
                      <th scope="col">SLA</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentTickets.map((ticket, index) => (
                      <tr key={`${ticket.id}-${index}`}>
                        <td className="col-id">#{ticket.id}</td>
                        <td className="col-title" title={ticket.title}>
                          {ticket.title}
                        </td>
                        <td>
                          <PBadge priority={ticket.priority} />
                        </td>
                        <td>
                          <StatusBadge status={ticket.status} />
                        </td>
                        <td className="col-assignee">
                          {ticket.assigned_to ?? "—"}
                        </td>
                        <td
                          className="col-id"
                          title={ticket.created_at}
                        >
                          {fmtDate(ticket.created_at)}
                        </td>
                        <td>
                          {ticket.breached ? (
                            <span className="breached-tag" role="status">BREACH</span>
                          ) : (
                            <span
                              style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: 10,
                                color: "var(--status-green)",
                              }}
                            >
                              OK
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
