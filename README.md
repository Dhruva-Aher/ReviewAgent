# PRBeliefs (ReviewAgent)

**GitHub App · institutional PR review** · Backend / AI tooling · Python · FastAPI · Redis

Reviews pull requests against **team beliefs** (past decisions and coding rules) via a webhook → Redis job queue → multi-agent review path — not a one-shot LLM comment bot.

[![CI](https://github.com/Dhruva-Aher/ReviewAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/Dhruva-Aher/ReviewAgent/actions/workflows/ci.yml)

| | |
|--|--|
| **Focus** | Beliefs memory · async review · GitHub App |
| **Stack** | FastAPI · Redis · SQLite · Groq LLaMA · Docker |
| **Proof** | **30** pytest cases · CI with Redis 7 |

---

## Highlights

- **Reliability** — Webhook intake queues work on Redis so review survives request timeouts; rate limiting on GitHub paths.
- **Correctness** — Beliefs schema + store; **30** automated tests in CI (`pytest` + Redis service).
- **Differentiation** — Parallel specialty agents (security, performance, style, architecture, dependency) routed by a supervisor, then grounded in **historical beliefs** before posting a structured GitHub review.
- **Operability** — Docker Compose local path; GitHub App install flow documented in-repo.

---

## Architecture

| Component | Responsibility |
|-----------|----------------|
| **GitHub App** | Webhooks on PR events |
| **API** | FastAPI — verify delivery, enqueue jobs |
| **Queue** | Redis-backed async workers |
| **Agents** | Parallel specialty reviewers |
| **Beliefs** | Persistent team decisions applied per PR |
| **Formatter** | Structured review comment → GitHub |

```text
GitHub PR → FastAPI webhook → Redis queue
                → multi-agent review + beliefs engine
                → structured comment on the PR
```

---

## Quick start

```bash
cp .env.example .env   # if present; set GitHub App + Groq keys
docker compose up --build
# or
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v
```

Configure a GitHub App pointing webhooks at your tunnel/API (`main.py` / `github_app.py`).

---

## For interview depth

| Topic | Where |
|-------|--------|
| Orchestration | `orchestrator.py`, `agents/` |
| Beliefs store | `store.py`, `prbeliefs.schema.json` |
| GitHub integration | `github.py`, `github_app.py` |
| Tests | `tests/` |
| Claim sheet | [docs/METRICS.md](docs/METRICS.md) |
| Decisions | [docs/DECISIONS.md](docs/DECISIONS.md) |

**Honesty:** Marketplace listing / production traffic are not resume metrics unless you have live install counts — pitch the **architecture** (queue + beliefs + fail-soft review) and the **30**-test suite.
