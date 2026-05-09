# AI-Driven Ticket Management & Helpdesk PoC

## Overview
A Proof of Concept (PoC) for an AI-driven helpdesk that acts as a smart "traffic controller" and problem solver. It answers 1st-line questions using text and screenshots, intelligently routes complex tickets to 2nd-line developers, and provides an SLA tracking dashboard.

## Project Type
WEB & BACKEND

## Success Criteria
- [ ] **Knowledge Ingestion**: Mock GitHub docs and work instructions loaded into memory.
- [ ] **1st-Line Resolution**: Chat UI accepts text + image, backend returns an AI-driven response based on mock data.
- [ ] **Intelligent Routing**: Unresolved issues automatically assign to a mock 2nd-line developer based on skill keywords.
- [ ] **SLA Dashboarding**: Management UI displays real-time ticket status against P1-P4 SLAs.

## Tech Stack
- **Frontend**: Next.js (React) + Tailwind CSS (Rapid UI, clean design).
- **Backend**: Python FastAPI (Fast, lightweight REST API).
- **AI**: Gemini Pro/Flash (or mock responses simulating multimodal AI).
- **Database**: In-memory Python structures / local JSON (To avoid over-engineering during the 8h hackathon constraints).

## File Structure
```text
/
├── backend/
│   ├── main.py              # FastAPI entrypoint
│   ├── data.py              # Mock data & in-memory store
│   ├── ai_service.py        # Mock Gemini/vision integration
│   └── routers/             # API routes (chat, tickets, sla)
└── frontend/
    ├── package.json
    ├── tailwind.config.js
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx     # Chat Interface (1st line)
    │   │   └── dashboard/   # SLA Dashboard
    │   └── components/      # ChatBubble, TicketTable, SLAStats
```

## Task Breakdown
- [x] **Task 1: Project Initialization** (Agent: `orchestrator`, Skill: `bash-linux`)
  - Create `/frontend` with `npx create-next-app` and `/backend` with FastAPI requirements.
  - → Verify: Both dev servers can start without errors.

- [x] **Task 2: Backend Mock Data & Ingestion (BB1)** (Agent: `backend-specialist`, Skill: `python-patterns`)
  - Create `data.py` with mock GitHub docs, users, and an in-memory ticket store.
  - → Verify: Can retrieve mock documents via a test function.

- [x] **Task 3: Backend Chat & Vision API (BB2)** (Agent: `backend-specialist`, Skill: `api-patterns`)
  - Create endpoint `/api/chat` that accepts text and image upload. Integrate mock AI logic.
  - → Verify: `curl` request to endpoint returns an AI response or escalation flag.

- [x] **Task 4: Backend Routing & SLA API (BB3 & BB4)** (Agent: `backend-specialist`, Skill: `api-patterns`)
  - Create `/api/tickets` to handle escalation matching logic and `/api/sla` to return ticket metrics.
  - → Verify: Calling the endpoints returns assigned tickets and SLA stats correctly.

- [x] **Task 5: Frontend Chat UI (BB2)** (Agent: `frontend-specialist`, Skill: `frontend-design`)
  - Build chat interface with text input and image upload. Connect to `/api/chat`.
  - → Verify: User can send a message and see the AI's response in the UI.

- [x] **Task 6: Frontend Dashboard UI (BB4)** (Agent: `frontend-specialist`, Skill: `frontend-design`)
  - Build SLA dashboard with metrics cards and a ticket table. Fetch from `/api/sla`.
  - → Verify: Dashboard renders correctly with data from backend.

## Done When (Phase X: Verification)
- [ ] Code Quality: `npm run lint` and `npx tsc --noEmit` pass in frontend.
- [ ] Backend: Starts with `uvicorn main:app` without errors.
- [ ] Flow Test: Send message with image -> Auto-escalate -> View routed ticket in Dashboard.
