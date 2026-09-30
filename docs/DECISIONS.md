# Decisions — PRBeliefs (ReviewAgent)

Related: [METRICS.md](./METRICS.md)

**Cross-verify (2026-09-30):** **30** tests counted; CI workflow present. No production install metrics.

---

## D1 — Institutional memory over one-shot LLM review

| | |
|--|--|
| **Context** | Generic PR bots restate style nits without team history. |
| **Decision** | Persist “beliefs” from past decisions and apply them on new PRs. |
| **Why** | Differentiator vs Copilot-comment clones. |
| **Evidence** | `store.py`, schema, beliefs engine path |
| **Status** | DECIDED · IMPLEMENTED |

---

## D2 — Async Redis queue behind webhooks

| | |
|--|--|
| **Context** | GitHub expects fast webhook ACK; LLM review is slow. |
| **Decision** | Enqueue jobs on Redis; workers run multi-agent review offline from the request. |
| **Why** | Reliability under GitHub delivery retries. |
| **Evidence** | docker-compose Redis; orchestrator |
| **Status** | DECIDED · IMPLEMENTED |

---

## D3 — Supervisor-routed specialty agents

| | |
|--|--|
| **Context** | Single mega-prompt is opaque and weak. |
| **Decision** | Parallel specialty agents + supervisor merge into structured comment. |
| **Tradeoffs** | More tokens/cost; clearer interview story. |
| **Evidence** | `agents/`, `orchestrator.py` |
| **Status** | DECIDED · IMPLEMENTED |

---

## D4 — Proof = pytest count, not Marketplace vanity

| | |
|--|--|
| **Context** | Temptation to claim “ships on Marketplace at scale”. |
| **Decision** | Public Y = **30** tests + architecture; installs = D until measured. |
| **Evidence** | `docs/METRICS.md` |
| **Status** | DECIDED |
