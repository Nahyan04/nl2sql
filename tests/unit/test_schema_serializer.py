from app.services.schema_serializer import serialize_schema


def _table(name: str, descriptor: str) -> dict:
    return {"name": name, "descriptor": descriptor}


def test_serialize_empty_tables_returns_empty_string() -> None:
    assert serialize_schema([]) == ""


def test_serialize_includes_each_table_descriptor() -> None:
    tables = [
        _table("orders", "orders(id, status)"),
        _table("customers", "customers(id, name)"),
    ]
    result = serialize_schema(tables)
    assert "orders(id, status)" in result
    assert "customers(id, name)" in result


def test_serialize_preserves_table_order() -> None:
    tables = [
        _table("orders", "orders(id, status)"),
        _table("customers", "customers(id, name)"),
        _table("products", "products(id, title)"),
    ]
    result = serialize_schema(tables)
    assert result.index("orders") < result.index("customers") < result.index("products")


def test_serialize_respects_char_budget_by_dropping_last_tables() -> None:
    # each descriptor is ~20 chars; budget of 25 fits only the first
    tables = [
        _table("orders", "orders(id, status)"),
        _table("customers", "customers(id, name)"),
    ]
    result = serialize_schema(tables, char_budget=25)
    assert "orders" in result
    assert "customers" not in result


def test_serialize_result_does_not_exceed_budget() -> None:
    tables = [_table(f"table{i}", f"table{i}(col_a, col_b)") for i in range(20)]
    budget = 100
    result = serialize_schema(tables, char_budget=budget)
    assert len(result) <= budget


def test_serialize_single_table_within_budget() -> None:
    tables = [_table("orders", "orders(id, status)")]
    result = serialize_schema(tables, char_budget=4000)
    assert "orders(id, status)" in result


def test_serialize_table_without_descriptor_falls_back_to_name() -> None:
    tables = [{"name": "orders"}]
    result = serialize_schema(tables)
    assert "orders" in result
