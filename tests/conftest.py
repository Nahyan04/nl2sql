from __future__ import annotations

import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, create_engine, text
from sqlalchemy.pool import StaticPool


@pytest.fixture
def sqlite_engine():
    """In-memory SQLite engine with a small seeded customers/orders schema.

    Uses StaticPool + check_same_thread=False so the same in-memory database
    is reachable from the worker thread FastAPI's TestClient runs requests on.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata = MetaData()

    Table(
        "customers",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(255), nullable=False),
    )
    Table(
        "orders",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("customer_id", Integer, ForeignKey("customers.id"), nullable=False),
        Column("status", String(50), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(text("INSERT INTO customers (id, name) VALUES (1, 'Alice')"))
        connection.execute(text("INSERT INTO orders (id, customer_id, status) VALUES (1, 1, 'shipped')"))

    yield engine
    engine.dispose()
