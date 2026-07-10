# Submission Document

## Project summary
This repository contains a compact FastAPI proof of concept for an API rate limiter. It uses an in-memory token bucket, applies organization-wide and endpoint-category limits, and enforces them through middleware before the route handler runs.

## Repository structure
- app/: FastAPI app, configuration, limiter, middleware, and stats helpers.
- config/: YAML configuration for plans, routes, and cleanup.
- tests/: Pytest coverage for limiter semantics, middleware behavior, configuration, and cleanup.
- docs/: submission, AI usage, decision, and video outline documents.
- scripts/: demo script.

## Run commands
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest -q
python scripts/demo_rate_limit.py
```

## Core design
- Token bucket per organization and per organization+endpoint category.
- Atomic decision under one in-process lock.
- Configurable route classification and plan mapping.
- Meaningful 429 responses with Retry-After and custom rate-limit headers.

## Configuration
The YAML configuration is in [config/rate_limits.yaml](config/rate_limits.yaml). The solution is loadable without editing source code, though a restart is required for this PoC.

## Example 429 response
```json
{
  "error": "rate_limit_exceeded",
  "message": "Write endpoint rate limit exceeded.",
  "limit_type": "endpoint",
  "endpoint_category": "write",
  "organization_id": "org-standard",
  "limit": 30,
  "window_seconds": 60,
  "retry_after_seconds": 2
}
```

## Test summary
The test suite covers limiter semantics, middleware responses, invalid configuration, and cleanup behavior.

## Architecture and trade-offs
This is a deliberately small in-process design aimed at a hiring challenge. It is correct for a local PoC but not for multi-replica production enforcement.

## Production-readiness plan
The README contains a short production-readiness plan and failure-mode discussion. The design would need Redis or another shared atomic store for production fairness across replicas.

## AI usage summary
The repository contains a draft AI usage log and a decision log that capture the main design choices and redirections made during the implementation.

## Repository placeholder
GitHub repository: [Replace with public repository URL]

CANDIDATE MUST COMPLETE WITHOUT AI ASSISTANCE

Describe a scenario where an AI coding assistant gives a plausible but incorrect answer for this problem. What would the incorrect output look like? How would you catch it before acting on it?
