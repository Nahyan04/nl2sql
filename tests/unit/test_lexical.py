from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, create_engine

from app.services.schema_introspector import introspect_schema
from app.services.retrieval.lexical import (
    build_table_descriptor,
    expand_with_fk_neighbors,
    retrieve,
    score_tables,
)


def _build_schema() -> dict:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    metadata = MetaData()
    Table("customers", metadata, Column("id", Integer, primary_key=True), Column("name", String(255)))
    Table(
        "orders",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("customer_id", Integer, ForeignKey("customers.id")),
        Column("status", String(50)),
    )
    Table("products", metadata, Column("id", Integer, primary_key=True), Column("title", String(255)))
    metadata.create_all(engine)
    return introspect_schema(engine)


def test_orders_outranks_products_for_order_question() -> None:
    schema = _build_schema()
    scores = score_tables("show me all orders", schema)
    ranked = [name for name, _ in scores]
    assert ranked.index("orders") < ranked.index("products")


def test_customers_outranks_products_for_customer_question() -> None:
    schema = _build_schema()
    scores = score_tables("list all customers", schema)
    ranked = [name for name, _ in scores]
    assert ranked.index("customers") < ranked.index("products")


def test_alias_boosts_orders_for_purchases_question() -> None:
    schema = _build_schema()
    aliases = {"purchases": ["orders", "order_items"]}
    scores = score_tables("list all purchases", schema, aliases)
    score_map = dict(scores)
    assert score_map["orders"] > score_map["products"]


def test_column_name_contributes_to_score() -> None:
    schema = _build_schema()
    # "status" is a column only on orders
    scores = score_tables("what is the order status", schema)
    score_map = dict(scores)
    # orders should score higher than customers for status query
    assert score_map["orders"] > score_map["customers"]


def test_fk_expansion_pulls_customers_when_orders_selected() -> None:
    schema = _build_schema()
    expanded = expand_with_fk_neighbors(["orders"], schema)
    assert "customers" in expanded


def test_fk_expansion_preserves_original_selection_order() -> None:
    schema = _build_schema()
    expanded = expand_with_fk_neighbors(["orders"], schema)
    assert expanded[0] == "orders"


def test_fk_expansion_does_not_duplicate_tables() -> None:
    schema = _build_schema()
    expanded = expand_with_fk_neighbors(["orders", "customers"], schema)
    assert expanded.count("customers") == 1
    assert expanded.count("orders") == 1


def test_fk_expansion_no_neighbors_returns_same_list() -> None:
    schema = _build_schema()
    expanded = expand_with_fk_neighbors(["products"], schema)
    assert "products" in expanded
    assert "orders" not in expanded
    assert "customers" not in expanded


def test_build_table_descriptor_includes_column_names() -> None:
    schema = _build_schema()
    orders_table = next(t for t in schema["tables"] if t["name"] == "orders")
    descriptor = build_table_descriptor(orders_table)
    assert "orders(" in descriptor
    assert "customer_id" in descriptor
    assert "status" in descriptor


def test_build_table_descriptor_includes_fk_references() -> None:
    schema = _build_schema()
    orders_table = next(t for t in schema["tables"] if t["name"] == "orders")
    descriptor = build_table_descriptor(orders_table)
    assert "customers" in descriptor


def test_build_table_descriptor_no_fk_has_no_fk_section() -> None:
    schema = _build_schema()
    customers_table = next(t for t in schema["tables"] if t["name"] == "customers")
    descriptor = build_table_descriptor(customers_table)
    assert "FK" not in descriptor


def test_retrieve_returns_orders_with_fk_expanded_customers() -> None:
    schema = _build_schema()
    results = retrieve("what are the latest orders", schema, top_n=1)
    result_names = [r["name"] for r in results]
    assert "orders" in result_names
    assert "customers" in result_names


def test_retrieve_results_include_descriptor_field() -> None:
    schema = _build_schema()
    results = retrieve("show orders", schema)
    for result in results:
        assert "descriptor" in result
