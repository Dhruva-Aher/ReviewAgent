# Contributing to PRBeliefs

First off, thank you for considering contributing to PRBeliefs! It's people like you that make this tool better for everyone.

## How Can I Contribute?

### Reporting Bugs
Bugs are tracked as GitHub issues. When creating an issue, please explain the problem and include additional details to help maintainers reproduce the problem.

### Suggesting Enhancements
Enhancement suggestions are also tracked as GitHub issues. Please provide a clear and descriptive title and a detailed description of the proposed enhancement.

### Pull Requests
1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests to the `tests/` directory.
3. Ensure the test suite passes (`pytest tests/`).
4. Make sure your code adheres to our linting rules (`ruff check .`).
5. Update the documentation if applicable.
6. Issue that pull request!

## Adding a New Agent
If you want to add a new specialized agent to the review pipeline:
1. Create your agent class in `agents/impl.py` or a new file in `agents/`.
2. Inherit from `BaseAgent`.
3. Implement `relevance_hint(context)` and `async run(context)`.
4. Register the agent in `orchestrator.py`.
5. Add appropriate tests in `tests/test_agents.py`.

## Code of Conduct
Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.
