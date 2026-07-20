from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Numeric, String, Table, func

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import get_engine

metadata = MetaData()

customers = Table(
    "customers",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255), nullable=False),
    Column("email", String(255), nullable=False, unique=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)

products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255), nullable=False),
    Column("sku", String(64), nullable=False, unique=True),
    Column("price", Numeric(10, 2), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)

orders = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("customer_id", Integer, ForeignKey("customers.id"), nullable=False),
    Column("status", String(50), nullable=False),
    Column("order_date", DateTime, nullable=False, server_default=func.now()),
)

order_items = Table(
    "order_items",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("order_id", Integer, ForeignKey("orders.id"), nullable=False),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("unit_price", Numeric(10, 2), nullable=False),
)

CUSTOMERS = [
    {"name": "Alice Chen", "email": "alice.chen@example.com"},
    {"name": "Marcus Webb", "email": "marcus.webb@example.com"},
    {"name": "Priya Nair", "email": "priya.nair@example.com"},
    {"name": "Diego Ramirez", "email": "diego.ramirez@example.com"},
    {"name": "Hana Kobayashi", "email": "hana.kobayashi@example.com"},
    {"name": "Liam O'Connor", "email": "liam.oconnor@example.com"},
    {"name": "Fatima Al-Sayed", "email": "fatima.alsayed@example.com"},
    {"name": "Noah Fischer", "email": "noah.fischer@example.com"},
]

PRODUCTS = [
    {"name": "Wireless Mouse", "sku": "SKU-1001", "price": "24.99"},
    {"name": "Mechanical Keyboard", "sku": "SKU-1002", "price": "79.99"},
    {"name": "USB-C Hub", "sku": "SKU-1003", "price": "34.50"},
    {"name": '27" Monitor', "sku": "SKU-1004", "price": "249.00"},
    {"name": "Laptop Stand", "sku": "SKU-1005", "price": "39.99"},
    {"name": "Noise Cancelling Headphones", "sku": "SKU-1006", "price": "149.99"},
    {"name": "Webcam 1080p", "sku": "SKU-1007", "price": "45.00"},
    {"name": "Desk Lamp", "sku": "SKU-1008", "price": "22.50"},
    {"name": "Ergonomic Office Chair", "sku": "SKU-1009", "price": "199.00"},
    {"name": "Standing Desk Converter", "sku": "SKU-1010", "price": "175.00"},
    {"name": "Notebook Set (3-pack)", "sku": "SKU-1011", "price": "12.99"},
    {"name": "Wireless Charging Pad", "sku": "SKU-1012", "price": "19.99"},
]

# customer index into CUSTOMERS, order status
ORDERS = [
    {"customer": 0, "status": "delivered"},
    {"customer": 1, "status": "delivered"},
    {"customer": 2, "status": "shipped"},
    {"customer": 0, "status": "pending"},
    {"customer": 3, "status": "delivered"},
    {"customer": 4, "status": "cancelled"},
    {"customer": 5, "status": "delivered"},
    {"customer": 6, "status": "processing"},
    {"customer": 7, "status": "delivered"},
    {"customer": 1, "status": "shipped"},
    {"customer": 2, "status": "delivered"},
    {"customer": 3, "status": "pending"},
    {"customer": 4, "status": "delivered"},
    {"customer": 5, "status": "delivered"},
    {"customer": 6, "status": "delivered"},
    {"customer": 0, "status": "shipped"},
    {"customer": 7, "status": "cancelled"},
    {"customer": 2, "status": "processing"},
    {"customer": 3, "status": "delivered"},
    {"customer": 6, "status": "delivered"},
]

# order index into ORDERS, product index into PRODUCTS, quantity
ORDER_ITEMS = [
    {"order": 0, "product": 1, "quantity": 2},
    {"order": 0, "product": 0, "quantity": 1},
    {"order": 1, "product": 3, "quantity": 1},
    {"order": 2, "product": 5, "quantity": 1},
    {"order": 2, "product": 8, "quantity": 1},
    {"order": 3, "product": 10, "quantity": 3},
    {"order": 4, "product": 4, "quantity": 1},
    {"order": 4, "product": 2, "quantity": 2},
    {"order": 5, "product": 6, "quantity": 1},
    {"order": 6, "product": 9, "quantity": 1},
    {"order": 7, "product": 11, "quantity": 2},
    {"order": 8, "product": 3, "quantity": 2},
    {"order": 9, "product": 0, "quantity": 1},
    {"order": 9, "product": 1, "quantity": 1},
    {"order": 10, "product": 7, "quantity": 2},
    {"order": 10, "product": 10, "quantity": 1},
    {"order": 11, "product": 5, "quantity": 1},
    {"order": 12, "product": 8, "quantity": 1},
    {"order": 12, "product": 9, "quantity": 1},
    {"order": 13, "product": 2, "quantity": 1},
    {"order": 14, "product": 4, "quantity": 2},
    {"order": 15, "product": 6, "quantity": 1},
    {"order": 15, "product": 11, "quantity": 1},
    {"order": 16, "product": 3, "quantity": 1},
    {"order": 17, "product": 0, "quantity": 3},
    {"order": 18, "product": 1, "quantity": 1},
    {"order": 18, "product": 5, "quantity": 1},
    {"order": 19, "product": 10, "quantity": 2},
    {"order": 19, "product": 7, "quantity": 1},
]


def seed(engine) -> None:
    metadata.drop_all(engine)
    metadata.create_all(engine)

    with engine.begin() as connection:
        customer_ids = [
            connection.execute(customers.insert().values(**row)).inserted_primary_key[0]
            for row in CUSTOMERS
        ]
        product_ids = [
            connection.execute(products.insert().values(**row)).inserted_primary_key[0]
            for row in PRODUCTS
        ]
        order_ids = [
            connection.execute(
                orders.insert().values(customer_id=customer_ids[row["customer"]], status=row["status"])
            ).inserted_primary_key[0]
            for row in ORDERS
        ]
        for row in ORDER_ITEMS:
            connection.execute(
                order_items.insert().values(
                    order_id=order_ids[row["order"]],
                    product_id=product_ids[row["product"]],
                    quantity=row["quantity"],
                    unit_price=PRODUCTS[row["product"]]["price"],
                )
            )


def main() -> None:
    engine = get_engine()
    try:
        seed(engine)
        print(
            f"seeded {len(CUSTOMERS)} customers, {len(PRODUCTS)} products, "
            f"{len(ORDERS)} orders, {len(ORDER_ITEMS)} order_items"
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
