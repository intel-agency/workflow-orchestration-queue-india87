# OS-APOW: Headless Agentic Orchestration Platform

OS-APOW is a groundbreaking headless agentic orchestration platform that transforms AI coding from an interactive experience to an autonomous background production service.

## Overview

The system natively integrates into existing Agile workflows by translating standard project management artifacts (GitHub Issues, Epics, Kanban boards) into automated Execution Orders.

## Architecture

The system is distributed across four conceptual pillars:

1. **The Ear (Work Event Notifier):** FastAPI-based webhook receiver for event ingestion
2. **The State (Work Queue):** GitHub Issues as the state management layer
3. **The Brain (Sentinel Orchestrator):** Background polling and task execution
4. **The Hands (Opencode Worker):** Isolated DevContainer execution environment

## Installation

```bash
# Install dependencies
uv sync --dev

# Run tests
uv run pytest

# Run the notifier service
uv run uvicorn src.notifier_service:app --reload

# Run the sentinel orchestrator
uv run python -m src.orchestrator_sentinel
```

## Configuration

Set the following environment variables:

- `GITHUB_TOKEN`: GitHub Personal Access Token
- `GITHUB_ORG`: GitHub organization name
- `GITHUB_REPO`: Repository name
- `WEBHOOK_SECRET`: GitHub App webhook secret
- `SENTINEL_BOT_LOGIN`: Bot account login (optional, for distributed locking)

## License

MIT
