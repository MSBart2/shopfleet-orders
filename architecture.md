# Architecture — shopfleet-orders

## Service Overview

| Property | Value |
|---|---|
| Role | Order processing microservice |
| Language | Python 3.11+ |
| Framework | FastAPI 0.111+ / Pydantic v2 |
| Default port | `3003` (override with `PORT` env var) |
| Persistence | None — in-memory dict, resets on restart |
| Entry point | `app/main.py` |

## Position in ShopFleet

```
shopfleet-shared  ──┐
shopfleet-users   ──┤──▶  shopfleet-orders  ──▶  shopfleet-payments
shopfleet-products──┘                        └──▶  shopfleet-notifications
```

Upstream (this service depends on): `shopfleet-shared`, `shopfleet-users`, `shopfleet-products`  
Downstream (depend on this service): `shopfleet-payments`, `shopfleet-notifications`

## Code Layout

```
shopfleet-orders/
├── app/
│   ├── __init__.py       # empty
│   └── main.py           # all models, routes, business logic
├── Dockerfile
├── pyproject.toml
├── acp-manifest.json
└── architecture.md
```

All application code is in a single file: `app/main.py`. There are no sub-packages, routers, or separate layers.

## Runtime

**Local:**
```bash
uvicorn app.main:app --reload --port 3003
```

**Docker:**
```dockerfile
FROM python:3.12-slim
EXPOSE 3003
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3003"]
```

## Data Store

A module-level dict in `main.py`:
```python
orders: dict[str, Order] = {}
```
No database. No persistence across restarts. No concurrency control.

---

## Data Models

### `OrderStatus` (str Enum)

| Value | Description |
|---|---|
| `pending` | Newly created, awaiting confirmation |
| `confirmed` | Confirmed, not yet in fulfillment |
| `processing` | In fulfillment / being picked & packed |
| `shipped` | Handed to carrier |
| `delivered` | Received by customer |
| `cancelled` | Cancelled (terminal) |
| `refunded` | Refunded after delivery (terminal) |

### `Address`

| Field | Type | Required |
|---|---|---|
| `line1` | `str` | ✓ |
| `line2` | `str \| None` | — |
| `city` | `str` | ✓ |
| `state` | `str` | ✓ |
| `postal_code` | `str` | ✓ |
| `country` | `str` | ✓ |

### `OrderItem`

| Field | Type | Notes |
|---|---|---|
| `product_id` | `str` | — |
| `product_name` | `str` | — |
| `quantity` | `int` | — |
| `price_per_unit` | `int` | **Cents**, not dollars |

### `Order` (canonical record)

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | UUID v4 |
| `user_id` | `str` | — |
| `items` | `list[OrderItem]` | — |
| `status` | `OrderStatus` | — |
| `subtotal` | `int` | Cents |
| `tax` | `int` | Cents; 8% of subtotal, truncated |
| `total` | `int` | Cents; `subtotal + tax` |
| `shipping_address` | `Address` | — |
| `created_at` | `str` | UTC ISO-8601, `Z` suffix |
| `updated_at` | `str` | UTC ISO-8601, `Z` suffix |

### Request Bodies

**`CreateOrderRequest`**
```json
{
  "user_id": "string",
  "items": [{ "product_id": "string", "product_name": "string", "quantity": 1, "price_per_unit": 1999 }],
  "shipping_address": { "line1": "string", "city": "string", "state": "string", "postal_code": "string", "country": "string" }
}
```

**`UpdateStatusRequest`**
```json
{ "status": "confirmed" }
```

---

## Endpoints

### `GET /health`

Health check. No auth.

**Response 200:**
```json
{ "status": "ok", "service": "orders", "order_count": 3 }
```

---

### `GET /`

List orders. Supports optional query-string filters.

**Query params:**

| Param | Type | Description |
|---|---|---|
| `user_id` | `str` | Filter to orders for this user |
| `status` | `OrderStatus` | Filter to orders with this status |

**Response 200:**
```json
{ "orders": [ /* Order[] */ ], "total": 2 }
```

---

### `GET /{order_id}`

Get a single order by ID.

**Response 200:** `Order` object  
**Response 404:** `{ "detail": "Order not found" }`

---

### `POST /`

Create a new order. Status is always set to `pending` on creation. `id`, `subtotal`, `tax`, `total`, `created_at`, and `updated_at` are server-generated.

**Request body:** `CreateOrderRequest`  
**Response 201:** Full `Order` object

**Tax calculation:** `tax = int(subtotal * 0.08)` — 8% flat rate, truncated (not rounded).

---

### `PATCH /{order_id}/status`

Advance or change the order status. Enforced by the state machine.

**Request body:** `UpdateStatusRequest`  
**Response 200:** Updated `Order` object  
**Response 400:** `{ "detail": "Cannot transition from <current> to <requested>" }`  
**Response 404:** `{ "detail": "Order not found" }`

---

## Order State Machine

```
pending ──────────────────────────────────────────┐
   │                                              ▼
   ├──▶ confirmed ──────────────────────────▶ cancelled (terminal)
   │        │
   │        └──▶ processing ──────────────▶ cancelled (terminal)
   │                  │
   │                  └──▶ shipped
   │                            │
   │                            └──▶ delivered
   │                                      │
   │                                      └──▶ refunded (terminal)
   │
   └──▶ cancelled (terminal)
```

**`VALID_TRANSITIONS` map (source of truth in `main.py`):**

| From | Allowed next states |
|---|---|
| `pending` | `confirmed`, `cancelled` |
| `confirmed` | `processing`, `cancelled` |
| `processing` | `shipped`, `cancelled` |
| `shipped` | `delivered` |
| `delivered` | `refunded` |
| `cancelled` | _(none)_ |
| `refunded` | _(none)_ |

Invalid transitions return HTTP 400. There is no force-override mechanism.

---

## Key Invariants

- All monetary values (`price_per_unit`, `subtotal`, `tax`, `total`) are **integers in cents**.
- Tax is always `int(subtotal * 0.08)` — hardcoded 8%, integer truncation.
- `id` fields are UUID v4 strings generated at creation time.
- Timestamps are UTC ISO-8601 strings with a trailing `Z` (not timezone-aware `datetime` objects).
- New orders always start in `pending` status regardless of what the caller sends.
- There is no authentication or authorization on any endpoint.
