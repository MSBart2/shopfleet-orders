from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid
import os

app = FastAPI(title="ShopFleet Orders", version="1.0.0")

class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"

class Address(BaseModel):
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str

class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    price_per_unit: int  # cents

class Order(BaseModel):
    id: str
    user_id: str
    items: list[OrderItem]
    status: OrderStatus
    subtotal: int
    tax: int
    total: int
    shipping_address: Address
    created_at: str
    updated_at: str

class CreateOrderRequest(BaseModel):
    user_id: str
    items: list[OrderItem]
    shipping_address: Address

class UpdateStatusRequest(BaseModel):
    status: OrderStatus

# In-memory store
orders: dict[str, Order] = {}

# State machine transitions
VALID_TRANSITIONS = {
    OrderStatus.pending: [OrderStatus.confirmed, OrderStatus.cancelled],
    OrderStatus.confirmed: [OrderStatus.processing, OrderStatus.cancelled],
    OrderStatus.processing: [OrderStatus.shipped, OrderStatus.cancelled],
    OrderStatus.shipped: [OrderStatus.delivered],
    OrderStatus.delivered: [OrderStatus.refunded],
    OrderStatus.cancelled: [],
    OrderStatus.refunded: [],
}

@app.get("/health")
def health():
    return {"status": "ok", "service": "orders", "order_count": len(orders)}

@app.get("/")
def list_orders(user_id: Optional[str] = None, status: Optional[OrderStatus] = None):
    results = list(orders.values())
    if user_id:
        results = [o for o in results if o.user_id == user_id]
    if status:
        results = [o for o in results if o.status == status]
    return {"orders": results, "total": len(results)}

@app.get("/{order_id}")
def get_order(order_id: str):
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found")
    return orders[order_id]

@app.post("/", status_code=201)
def create_order(req: CreateOrderRequest):
    subtotal = sum(item.price_per_unit * item.quantity for item in req.items)
    tax = int(subtotal * 0.08)  # 8% tax
    total = subtotal + tax
    
    order = Order(
        id=str(uuid.uuid4()),
        user_id=req.user_id,
        items=req.items,
        status=OrderStatus.pending,
        subtotal=subtotal,
        tax=tax,
        total=total,
        shipping_address=req.shipping_address,
        created_at=datetime.utcnow().isoformat() + "Z",
        updated_at=datetime.utcnow().isoformat() + "Z",
    )
    orders[order.id] = order
    return order

@app.patch("/{order_id}/status")
def update_order_status(order_id: str, req: UpdateStatusRequest):
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = orders[order_id]
    if req.status not in VALID_TRANSITIONS[order.status]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {order.status} to {req.status}"
        )
    
    order.status = req.status
    order.updated_at = datetime.utcnow().isoformat() + "Z"
    orders[order_id] = order
    return order

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "3003"))
    uvicorn.run(app, host="0.0.0.0", port=port)
