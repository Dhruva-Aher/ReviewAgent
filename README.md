# 🧠 PRBeliefs — Institutional Memory for Code Reviews

> Apply your team’s past decisions to every pull request — automatically.

PRBeliefs is an AI-powered GitHub App that reviews pull requests using **institutional knowledge from past PRs**, ensuring consistency, preventing regressions, and enforcing team decisions at scale.

---

## 🚀 Why PRBeliefs?

Traditional code review tools:
- ❌ Don’t remember past decisions  
- ❌ Re-flag the same issues repeatedly  
- ❌ Lose context across PRs  

PRBeliefs introduces:

> **Persistent team memory → applied in real-time to every PR**

---

## ⚙️ How It Works

GitHub PR
   ↓
Webhook (FastAPI)
   ↓
Async Job Queue (Redis)
   ↓
Multi-Agent Review System (parallel)
   ↓
Beliefs Engine (historical context)
   ↓
Structured Review Comment → GitHub
🧩 System Architecture
🔹 Multi-Agent Review System


---

## 🧩 System Architecture

### 🔹 Multi-Agent Review System

PRBeliefs uses a **supervisor-routed multi-agent architecture**:

- Security Agent → detects vulnerabilities  
- Performance Agent → flags inefficiencies  
- Style Agent → enforces conventions  
- Architecture Agent → checks system design  
- Dependency Agent → validates libraries  

All agents run **in parallel** using `asyncio.gather`, then results are aggregated and ranked.

---

### 🔹 Beliefs Engine (Core Innovation)

PRBeliefs stores **team decisions from previous PRs**:

```json
{
  "rule": "Avoid pymysql",
  "reason": "Performance issues in production",
  "source_pr": 47
}

These beliefs are:

Persisted (SQLite)
Retrieved during review
Applied to new PRs automatically
🔹 Async Processing Pipeline
GitHub Webhooks → ingested via FastAPI
Jobs queued in Redis
Workers process reviews asynchronously
Decouples ingestion from execution latency
📊 Example Output
PR #42 Review:

[Performance Agent]
❌ Inefficient database query detected
Confidence: 0.88

[Style Agent]
⚠️ Naming inconsistency in variable 'usrData'
Confidence: 0.76

[Beliefs Engine]
❌ Violates team rule: avoid pymysql
→ Referenced from PR #47

Final Recommendation:
- Refactor query (High Priority)
- Replace pymysql dependency (High Priority)
⚡ Performance
⚡ Parallel agent execution via asyncio.gather
⚡ Sub-second review latency (LLM via Groq)
⚡ Redis-backed queue for scalability
⚡ Per-installation rate limiting
🛠️ Tech Stack
Backend: FastAPI (Python)
AI: LLaMA 3.3 70B (via Groq API)
Queue: Redis
Persistence: SQLite (beliefs store)
Infra: Docker Compose + GitHub Actions (CI/CD)
Integration: GitHub App (webhooks + PR comments)
📦 Installation
Install the GitHub App:
👉 https://github.com/apps/prbeliefs
Clone repo:
git clone https://github.com/Dhruva-Aher/ReviewAgent.git
cd ReviewAgent
Run locally:
docker-compose up --build
Configure environment variables:
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY=
GROQ_API_KEY=
🧪 Testing
pytest

Includes:

Webhook handling tests
Authentication validation
Review pipeline coverage
🎯 Roadmap
 Hosted dashboard for belief management
 Team-specific rule customization UI
 Persistent vector search for semantic beliefs
 Org-wide analytics on recurring issues
🤝 Contributing

Open to ideas, feedback, and contributions — especially around:

Agent design
Review accuracy
Scaling architecture
📄 License

MIT

💡 What this README fixes (so you understand why it works)

This version:

Proves your system exists (architecture + flow)
Makes multi-agent claim visible
Shows real output
Explains your core innovation (beliefs)
Adds engineering credibility (queue, async, infra)
