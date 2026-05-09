# AI-Driven Ticket Management & Helpdesk PoC

An intelligent, multimodal helpdesk Proof of Concept (PoC) built for rapid issue resolution. This system provides a 1st-line AI support chat, intelligent 2nd-line ticket routing based on developer skills, and a real-time SLA management dashboard.

---

## 🚀 Project Overview

This hackathon PoC demonstrates an end-to-end AI support workflow:

1. **Multimodal Chat:** Users can describe their issues and attach screenshots.
2. **1st-Line AI Resolution:** The system uses the Hugging Face Inference API to analyze the issue against an in-memory knowledge base. If resolvable, the AI provides a direct, conversational answer.
3. **Intelligent Routing:** If the issue cannot be resolved by the AI, it is automatically escalated and assigned to a specific developer based on a skill-matching algorithm (e.g., matching `database` or `auth` tags).
4. **SLA Dashboard:** A live dashboard tracks ticket statuses, resolution rates, and SLA breaches across different priority levels (P1-P4).

---

## 🛠 Tech Stack

### Frontend

* **Framework:** Next.js (App Router)
* **Styling:** Vanilla CSS (Custom "Industrial Terminal" aesthetic)
* **Fonts:** Inter & IBM Plex Mono

### Backend

* **Framework:** FastAPI (Python)
* **AI Integration:** Hugging Face Hub (`InferenceClient`) using dynamic models:

  * `Qwen/Qwen2.5-7B-Instruct` for text
  * `meta-llama/Llama-3.2-11B-Vision-Instruct` for image analysis
* **Data Layer:** In-memory Pydantic data structures (Mock KB, Developers, Tickets)

---

## ✨ Features

* **Terminal-Inspired UI:** A high-contrast, sharp-edged interface devoid of common SaaS clichés.
* **Image Support:** Automatic compression and base64 encoding of user screenshots for multimodal AI analysis.
* **Dynamic LLM Routing:** The backend forces the LLM to output strict JSON, determining if the ticket is `resolved` (with an answer) or needs `routing` (with extracted skill tags).
* **Skill-Based Assignment:** Unresolved tickets are matched to mock developers (e.g., "Alice Chen" for `auth`) based on current workload and skill overlap.
* **Real-time Dashboard:** Asymmetric grid layout displaying live P1-P4 metrics, SLA targets, and recent ticket activity, polling the backend automatically.

---

## 💬 Example Interactions

Here are a few examples demonstrating how the AI evaluates and routes user queries.

### 1. AI Resolves Issue Directly (No Ticket Created)

When a user asks a question explicitly covered in the Knowledge Base, the AI acts as a chatbot and resolves it instantly.

> **User:** "How do I get a new access token when my JWT expires?"
>
> **AI:** "To get a new access token, you can use the `POST /api/auth/refresh` endpoint with a valid refresh token. Tokens expire after 24 hours."

---

### 2. Issue Escalated to Developer (Ticket Created)

When a user asks for an action, permission, or a fix that is not explicitly in the Knowledge Base, the AI safely routes it to the correct department.

> **User:** "The new hero image on the landing page is not responsive on mobile devices; it overflows the screen width."
>
> **AI:** "⚠️ I was unable to resolve this from the knowledge base. I've escalated ticket `#a1b2c3d4` with priority `P3` to `David Kim` based on the required skills (`frontend`). You'll hear back shortly."

---

### 3. Multimodal Analysis (Text + Image Upload)

The system uses a Vision-Language Model to read user screenshots and combine that visual context with the text prompt.

> **User:** *(Uploads terminal screenshot showing an `HTTP/1.1 401 Unauthorized` error)*
>
> "I am trying to refresh my session, but I keep getting an error in my console. Here is what I see. What is going wrong?"
>
> **AI:** "Thank you for providing that screenshot. I see that you are attempting to POST to our `/api/auth/refresh` endpoint and receiving an `HTTP 401: Unauthorized` error. According to our Authentication Guide, protected requests require validation. You must explicitly include the valid access token in your request header. Try updating your command to include `-H \"Authorization: Bearer <your_token>\"`."

---

## 📁 Project Structure

```text
ai-driven-ticket-management-helpdesk/
├── backend/
│   ├── routers/
│   │   ├── chat.py       # POST /api/chat (Handles user messages)
│   │   ├── sla.py        # GET /api/sla (Aggregates SLA metrics)
│   │   └── tickets.py    # GET /api/tickets & routing logic
│   ├── ai_service.py     # Hugging Face integration & JSON parsing
│   ├── data.py           # In-memory KB, tickets, and developer mock data
│   ├── main.py           # FastAPI entry point & CORS configuration
│   └── requirements.txt  # Python dependencies
└── frontend/
    ├── app/
    │   ├── components/
    │   │   └── TopBar.js # Shared navigation
    │   ├── dashboard/
    │   │   └── page.js   # SLA Dashboard UI
    │   ├── globals.css   # Industrial Terminal design system
    │   ├── layout.js     # Root layout with fonts
    │   └── page.js       # Main Chat UI
    └── package.json      # Node dependencies
```

---

## ⚙️ Environment Setup

To run the backend AI services, you must provide a Hugging Face API key.

### 1. Create a `.env` file in the `backend/` directory

```bash
cp backend/.env.example backend/.env
```

### 2. Configure the environment variables

Open `backend/.env` and configure the following variables:

```env
# Your Hugging Face token
# https://huggingface.co/settings/tokens
HUGGINGFACE_API_KEY=hf_your_actual_token_here

# Deployment environment identifier
NODE_ENV=development
```

> **Note:** The `backend/.gitignore` is configured to prevent committing `.env` files.

---

## 💻 Installation & Running Locally

The application requires running both the backend API and the frontend development server simultaneously.

### 1. Start the FastAPI Backend

Open a terminal, navigate to the `backend` folder, install dependencies, and start Uvicorn:

```bash
cd backend

# Create and activate a virtual environment (Windows example)
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Start the API server
uvicorn main:app --reload --port 8000
```

The backend will be available at:

```text
http://localhost:8000
```

---

### 2. Start the Next.js Frontend

Open a second terminal, navigate to the `frontend` folder, install packages, and start the Next.js development server:

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The frontend will be available at:

```text
http://localhost:3000
```

---

## 🧪 Demo Workflow

1. Open the chat interface.
2. Ask a question related to the knowledge base.
3. Upload screenshots for multimodal analysis.
4. Trigger unresolved scenarios to create routed tickets.
5. Open the dashboard to monitor SLA metrics and ticket activity.

---

## 📌 Notes

* This project uses in-memory storage and is intended for Proof-of-Concept and hackathon demonstrations.
* The AI response flow is powered through Hugging Face-hosted LLMs.
* The dashboard automatically polls the backend for real-time updates.

---

## 👨‍💻 Development Purpose

Developed for rapid iteration during a hackathon to demonstrate:

* AI-powered helpdesk automation
* Intelligent ticket escalation workflows
* Multimodal support systems
* Real-time SLA monitoring
* Modern full-stack architecture with Next.js and FastAPI
