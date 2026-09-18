# RecoverAI — Autonomous AI Revenue Recovery Platform

RecoverAI is a production-ready, multi-tenant revenue recovery platform that detects payment failures, churn risks, and checkout abandonments, predicts recovery likelihood via machine learning, and orchestrates remediation workflows through a secured Model Context Protocol (MCP) tool gateway.

---

## 🏛 Architecture Overview

```
                        ┌───────────────────────────────┐
                        │      Frontend (Next.js 14)    │
                        │    Port 3000 (React / App)    │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │       Backend (FastAPI)       │
                        │      Port 8000 (REST API)     │
                        └───────┬───────────────┬───────┘
                                │               │
                                ▼               ▼
            ┌───────────────────────┐       ┌────────────────────────┐
            │ PostgreSQL 16 DB      │       │ Standalone MCP Server  │
            │ Port 5432             │       │ Port 8080 (FastMCP)    │
            └───────────────────────┘       └────────────────────────┘
```

- **Frontend**: Next.js 14 with TypeScript, Tailwind CSS, live dashboard, cases audit timeline, and demo center.
- **Backend**: FastAPI with SQLAlchemy ORM, rate limiting, JWT authentication, and structured ML pipeline.
- **PostgreSQL**: Production-grade relational database with connection pooling and automated health checks.
- **MCP Server**: FastMCP server isolating payment remediation tools behind token authentication and merchant scoping.

---

## 🚀 Quick Start with Docker Compose

### 1. Clone and Configure Environment
```bash
cp .env.example .env
```

### 2. Launch All Services
```bash
docker-compose up --build -d
```

### 3. Verify Service Status
```bash
docker-compose ps
```

### 4. Access the Applications
- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **MCP Server**: [http://localhost:8080](http://localhost:8080)

---

## 💻 Local Development Setup (Without Docker)

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- PostgreSQL (or local SQLite fallback)

### Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### MCP Server Setup
```bash
cd mcp_server
pip install -r requirements.txt
python server.py
```

---

## 🩺 Health Check Endpoints

| Service | Endpoint | Description |
|---|---|---|
| **Backend Root Health** | `GET http://localhost:8000/health` | Service status, database connectivity, ML model readiness |
| **Backend API Health** | `GET http://localhost:8000/api/v1/health` | API v1 status and feature flags |
| **Frontend Health** | `GET http://localhost:3000/` | Next.js server liveness |
| **MCP Server Health** | FastMCP Tool `health_check(token)` / `ping()` | Tool availability and database status |

---

## 🧪 Running Automated Tests

### Backend Tests
```bash
cd backend
python -m pytest
```

### MCP Server Tests
```bash
cd mcp_server
python -m pytest
```

### Frontend Build & Typecheck
```bash
cd frontend
npm run build
```

---

## 🔒 Security & Safe Simulation

- **No Hardcoded Secrets**: All keys, passwords, and tokens are read strictly from environment variables.
- **Safe Mode**: Payment links and retries run in safe simulation mode by default (`RAZORPAY_ENABLED=false`).
- **Audit Logging**: Every tool execution is recorded in `mcp_tool_calls` with request parameters, caller identity, execution duration, and response status.
