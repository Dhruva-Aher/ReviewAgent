# Metrics & Claims — PRBeliefs (ReviewAgent)

**Cross-verified:** 2026-09-30

| ID | Claim (exact) | Grade | Evidence |
|----|---------------|-------|----------|
| C1 | GitHub App webhook → FastAPI → Redis queue → multi-agent review → GitHub comment | A | `main.py`, `github_app.py`, `orchestrator.py`, `agents/` |
| C2 | Beliefs persistence + schema | A | `store.py`, `prbeliefs.schema.json` |
| C3 | **30** pytest cases | A | `rg 'def test_'` under `tests/` = **30** (2026-09-30) |
| C4 | CI: pytest + Redis 7 service + ruff | A | `.github/workflows/ci.yml` |
| C5 | Specialty agents (security, performance, style, architecture, dependency) | A | `agents/` package layout |
| C6 | Marketplace install counts / production PR volume | D | Not measured — do not claim |

## Non-claims

| Phrase | Why |
|--------|-----|
| “Prevents regressions at scale for N teams” | No install telemetry in-repo |
| Exact review latency / cost per PR | No harness archived |

## Re-verify

```bash
pip install -r requirements.txt -r requirements-dev.txt
REDIS_URL=redis://localhost:6379 pytest tests/ -v
```
