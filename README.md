# PRBeliefs

Your team's institutional memory, applied to every pull request.

## How it works

PRBeliefs is a persistent, context-aware code review system that remembers past architectural decisions, project conventions, and team preferences. Unlike stateless LLM reviewers that make the same suggestions on every PR, PRBeliefs learns from your feedback and enforces team-specific guidelines by extracting rules from historical pull requests and persisting them in a local SQLite database.

When a new pull request is opened or updated, PRBeliefs intercepts the webhook event and dispatches the diff to a Redis queue. A background worker picks up the job and orchestrates a multi-agent review pipeline. Several specialized agents analyze the code in parallel—focusing on security, performance, architecture, dependencies, and test coverage—each applying the learned repository rules to their analysis. 

Finally, a synthesis agent aggregates the findings, deduplicates overlapping feedback, filters out low-confidence suggestions, and posts the results directly back to GitHub. It adds inline comments on specific lines of code and updates the commit status badge, ensuring the author gets highly relevant, historically informed feedback without being overwhelmed.

## Architecture

```text
GitHub PR
   │
   ▼
Webhook (FastAPI)
   │
   ▼
Redis Queue
   │
   ▼
Worker (Python)
   │
   ▼
Supervisor (Orchestrator)
   │
   ├──► Security Agent
   ├──► Architecture Agent
   ├──► Performance Agent
   ├──► TestCoverage Agent
   └──► Dependency Agent
   │
   ▼
Synthesis Agent
   │
   ▼
GitHub Inline Comments + Status Badge
```

## Agents

| Name               | Focus                                       | When it runs                                    |
|--------------------|---------------------------------------------|-------------------------------------------------|
| SecurityAgent      | Vulnerabilities, injections, secrets        | Python, JavaScript, Config files                |
| ArchitectureAgent  | Project patterns, structural design         | Python, core logic files                        |
| PerformanceAgent   | Algorithmic complexity, expensive operations| Computation-heavy files, data processing        |
| TestCoverageAgent  | Missing assertions, edge cases              | Test files (`test_*.py`, etc.)                  |
| DependencyAgent    | Outdated packages, licensing issues         | `requirements.txt`, `package.json`, `Pipfile`   |
| SynthesisAgent     | Aggregation, deduplication, formatting      | Always runs after specialized agents            |

## Quick start

1. Clone the repository: `git clone https://github.com/your-org/PRBeliefs.git && cd PRBeliefs`
2. Copy the example environment file: `cp .env.example .env`
3. Fill in your `GROQ_API_KEY` and `GITHUB_TOKEN` in the `.env` file.
4. Start the application using Docker Compose: `docker-compose up --build`

## Local dev

1. Ensure Redis is running locally (`redis-server`).
2. Create and activate a Python virtual environment: `python -m venv venv && source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt -r requirements-dev.txt`
4. Copy `.env.example` to `.env` and configure your credentials.
5. Start the web server: `uvicorn main:app --reload --port 8001`
6. In a new terminal, start the queue worker: `python queue_worker.py`

## Configuration

| Setting in `.prbeliefs.yml` | Description                                            | Default |
|-----------------------------|--------------------------------------------------------|---------|
| `multi_agent`               | Whether to use the full multi-agent pipeline           | `true`  |
| `confidence_threshold`      | Minimum score (0-100) to post a review comment         | `60`    |
| `ignored_paths`             | List of glob patterns to exclude from review           | `[]`    |

## Slash commands

| Command               | Description                                           |
|-----------------------|-------------------------------------------------------|
| `/review`             | Force an immediate re-review of the pull request      |
| `/beliefs list`       | Show all currently active rules for the repository    |
| `/beliefs add <rule>` | Add a new rule to the repository's institutional memory|
| `/beliefs remove <id>`| Remove an existing rule by its ID                     |

## API reference

| Method | Endpoint         | Description                                       |
|--------|------------------|---------------------------------------------------|
| GET    | `/health`        | Health check endpoint for monitoring              |
| GET    | `/beliefs`       | Retrieve all stored beliefs and past decisions    |
| POST   | `/beliefs`       | Add a new rule or past decision to the database   |
| POST   | `/review`        | Trigger a synchronous review (for local testing)  |
| POST   | `/webhook`       | GitHub App webhook receiver                       |
| GET    | `/stats`         | System statistics (queue length, processed PRs)   |
| GET    | `/agent-stats`   | Performance and invocation metrics for each agent |

## Contributing

1. Fork the repository and create your feature branch.
2. Add your new agent class to the `agents/` directory, inheriting from the base `Agent` class.
3. Implement the `relevance_hint` method to define when your agent should run based on the diff.
4. Implement the `run` method to analyze the code and return an `AgentResult`.
5. Add your new agent to the supervisor registry in `orchestrator.py` and write unit tests in `tests/test_agents.py`. Submit a PR!
