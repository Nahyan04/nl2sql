from app.services.sql_validator import validate_read_only


def test_accepts_simple_select() -> None:
    result = validate_read_only("SELECT id, name FROM customers")
    assert result.is_safe is True
    assert result.reason == ""


def test_accepts_with_clause() -> None:
    result = validate_read_only("WITH recent AS (SELECT id FROM orders) SELECT * FROM recent")
    assert result.is_safe is True


def test_accepts_union_query() -> None:
    result = validate_read_only("SELECT id FROM customers UNION SELECT id FROM orders")
    assert result.is_safe is True


def test_rejects_select_into() -> None:
    result = validate_read_only("SELECT * INTO new_table FROM customers")
    assert result.is_safe is False


def test_rejects_insert() -> None:
    result = validate_read_only("INSERT INTO customers (id, name) VALUES (1, 'a')")
    assert result.is_safe is False


def test_rejects_update() -> None:
    result = validate_read_only("UPDATE orders SET status = 'shipped'")
    assert result.is_safe is False


def test_rejects_delete() -> None:
    result = validate_read_only("DELETE FROM orders WHERE id = 1")
    assert result.is_safe is False


def test_rejects_drop() -> None:
    result = validate_read_only("DROP TABLE customers")
    assert result.is_safe is False


def test_rejects_create() -> None:
    result = validate_read_only("CREATE TABLE customers (id INT)")
    assert result.is_safe is False


def test_rejects_alter() -> None:
    result = validate_read_only("ALTER TABLE customers ADD COLUMN age INT")
    assert result.is_safe is False


def test_rejects_truncate() -> None:
    result = validate_read_only("TRUNCATE TABLE customers")
    assert result.is_safe is False


def test_rejects_grant() -> None:
    result = validate_read_only("GRANT SELECT ON customers TO alice")
    assert result.is_safe is False


def test_rejects_mutating_statement_hidden_in_cte() -> None:
    raw = "WITH deleted AS (DELETE FROM orders RETURNING id) SELECT * FROM deleted"
    result = validate_read_only(raw)
    assert result.is_safe is False


def test_rejects_stacked_statements() -> None:
    result = validate_read_only("SELECT 1; DROP TABLE customers;")
    assert result.is_safe is False


def test_treats_malformed_sql_as_unsafe() -> None:
    result = validate_read_only("SELEC * FROM customers")
    assert result.is_safe is False


def test_treats_empty_string_as_unsafe() -> None:
    result = validate_read_only("")
    assert result.is_safe is False
