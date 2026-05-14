# ShopFleet Orders Service

Order processing with state machine for ShopFleet. Built with Python and FastAPI.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List orders (filter by user_id, status) |
| GET | `/{order_id}` | Get order by ID |
| POST | `/` | Create new order |
| PATCH | `/{order_id}/status` | Update order status |
| GET | `/health` | Service health check |

## Order State Machine

```
pending → confirmed → processing → shipped → delivered → refunded
    ↓         ↓            ↓
cancelled  cancelled   cancelled
```

## Development

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 3003
```

Runs on port 3003 by default.

## Part of ShopFleet

This Python service demonstrates cross-language coordination in the ShopFleet microservices demo.
