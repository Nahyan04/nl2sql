from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, create_engine

from app.services.schema_introspector import introspect_schema


def test_introspect_schema_returns_table_column_and_fk_metadata() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
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
        Column("notes", String(255), nullable=True),
    )
    metadata.create_all(engine)

    schema = introspect_schema(engine)

    assert schema["schema"] == "main"
    assert [table["name"] for table in schema["tables"]] == ["customers", "orders"]

    customers_table = schema["tables"][0]
    assert customers_table["primary_key"] == ["id"]
    assert customers_table["foreign_keys"] == []
    assert customers_table["columns"] == [
        {"name": "id", "type": "INTEGER", "nullable": False},
        {"name": "name", "type": "VARCHAR(255)", "nullable": False},
    ]

    orders_table = schema["tables"][1]
    assert orders_table["primary_key"] == ["id"]
    assert orders_table["columns"] == [
        {"name": "id", "type": "INTEGER", "nullable": False},
        {"name": "customer_id", "type": "INTEGER", "nullable": False},
        {"name": "status", "type": "VARCHAR(50)", "nullable": False},
        {"name": "notes", "type": "VARCHAR(255)", "nullable": True},
    ]
    assert orders_table["foreign_keys"] == [
        {
            "name": None,
            "columns": ["customer_id"],
            "referred_schema": None,
            "referred_table": "customers",
            "referred_columns": ["id"],
        }
    ]


def test_introspect_schema_handles_empty_schemas() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    schema = introspect_schema(engine)

    assert schema == {"schema": "main", "tables": []}
