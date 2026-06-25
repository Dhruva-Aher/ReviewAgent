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

```
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
```

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
```

These beliefs are:
- Persisted (SQLite)
- Retrieved during review
- Applied to new PRs automatically

---

### 🔹 Async Processing Pipeline

- GitHub Webhooks → ingested via FastAPI  
- Jobs queued in Redis  
- Workers process reviews asynchronously  
- Decouples ingestion from execution latency  

---

## 📊 Example Output

```
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
```

---

## ⚡ Performance

- ⚡ Parallel agent execution via `asyncio.gather`
- ⚡ Sub-second review latency (LLM via Groq)
- ⚡ Redis-backed queue for scalability
- ⚡ Per-installation rate limiting

---

## 🛠️ Tech Stack

- **Backend:** FastAPI (Python)  
- **AI:** LLaMA 3.3 70B (via Groq API)  
- **Queue:** Redis  
- **Persistence:** SQLite (beliefs store)  
- **Infra:** Docker Compose + GitHub Actions (CI/CD)  
- **Integration:** GitHub App (webhooks + PR comments)  

---

## 📦 Installation

1. Install the GitHub App:  
👉 https://github.com/apps/prbeliefs  

2. Clone repo:
```bash
git clone https://github.com/Dhruva-Aher/ReviewAgent.git
cd ReviewAgent
```

3. Run locally:
```bash
docker-compose up --build
```

4. Configure environment variables:
```
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY=
GROQ_API_KEY=
```

---

## 🧪 Testing

```bash
pytest
```

Includes:
- Webhook handling tests  
- Authentication validation  
- Review pipeline coverage  

---

## 🎯 Roadmap

- [ ] Hosted dashboard for belief management  
- [ ] Team-specific rule customization UI  
- [ ] Persistent vector search for semantic beliefs  
- [ ] Org-wide analytics on recurring issues  

---

## 🤝 Contributing

Open to ideas, feedback, and contributions — especially around:
- Agent design  
- Review accuracy  
- Scaling architecture  

1. Fork the repository and create your feature branch.
2. Add your new agent class to the `agents/` directory, inheriting from the base `Agent` class.
3. Implement the `relevance_hint` method to define when your agent should run based on the diff.
4. Implement the `run` method to analyze the code and return an `AgentResult`.
5. Add your new agent to the supervisor registry in `orchestrator.py` and write unit tests in `tests/test_agents.py`. Submit a PR!

Please see our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) for more information.

---

## 🛡️ Support & Security

* **Support & Help:** See [SUPPORT.md](SUPPORT.md) for help, bug reports, and feature requests.
* **Privacy Policy:** See [PRIVACY.md](PRIVACY.md) to understand how we handle your data.
* **Security:** See [SECURITY.md](SECURITY.md) for vulnerability reporting instructions.

---

## 📄 License

MIT
