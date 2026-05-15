# Copilot Instructions — shopfleet-orders

> For architecture, endpoints, data models, and contracts, see [`architecture.md`](../architecture.md).

## Commands

```bash
# Install (including dev dependencies)
pip install -e ".[dev]"

# Run locally
uvicorn app.main:app --reload --port 3003

# Test
pytest
pytest tests/path/to/test_file.py::test_function_name  # single test

# Lint
ruff check .
```

Line length limit: **100** (enforced by ruff).

## Coding Conventions

**All code lives in `app/main.py`.** There are no sub-packages or routers — keep new logic in the same file unless explicitly restructuring.

**Monetary values are always integers in cents.** Never use floats for money.

**Timestamps** are plain UTC ISO-8601 strings with a `Z` suffix: `datetime.utcnow().isoformat() + "Z"`.

**Pydantic v2 models** — `OrderStatus` extends both `str` and `Enum` so it serializes as a plain string. Request/response models are plain `BaseModel` subclasses with no ORM layer.

**Order state transitions must go through `VALID_TRANSITIONS`** — do not bypass the dict or add ad-hoc status assignments.
