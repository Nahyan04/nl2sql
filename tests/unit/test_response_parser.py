from app.services.response_parser import parse_response


def test_parses_clean_sql_tag_output() -> None:
    raw = "Sure, here you go:\n<sql>SELECT id, total FROM orders WHERE status = 'paid'</sql>"
    result = parse_response(raw)
    assert result is not None
    assert result.query == "SELECT id, total FROM orders WHERE status = 'paid'"
    assert result.is_valid is True


def test_sql_tag_takes_priority_over_fenced_block() -> None:
    raw = (
        "<sql>SELECT * FROM customers</sql>\n"
        "```sql\nDROP TABLE customers\n```"
    )
    result = parse_response(raw)
    assert result is not None
    assert result.query == "SELECT * FROM customers"


def test_parses_fenced_sql_code_block() -> None:
    raw = "Here is the query:\n```sql\nSELECT name FROM customers;\n```"
    result = parse_response(raw)
    assert result is not None
    assert result.query == "SELECT name FROM customers"


def test_parses_unlabeled_fenced_block() -> None:
    raw = "```\nSELECT 1\n```"
    result = parse_response(raw)
    assert result is not None
    assert result.query == "SELECT 1"


def test_parses_plain_text_select_fallback() -> None:
    raw = "SELECT count(*) FROM orders"
    result = parse_response(raw)
    assert result is not None
    assert result.query.startswith("SELECT count(*)")


def test_parses_plain_sql_after_leading_blank_lines() -> None:
    raw = "\n\nSELECT id FROM orders\n"
    result = parse_response(raw)
    assert result is not None
    assert result.query == "SELECT id FROM orders"


def test_parses_with_clause() -> None:
    raw = "<sql>WITH recent AS (SELECT id FROM orders) SELECT * FROM recent</sql>"
    result = parse_response(raw)
    assert result is not None
    assert result.query.startswith("WITH recent")


def test_strips_trailing_semicolon() -> None:
    raw = "<sql>SELECT 1;</sql>"
    result = parse_response(raw)
    assert result is not None
    assert result.query == "SELECT 1"


def test_returns_none_on_empty_input() -> None:
    assert parse_response("") is None
    assert parse_response("   \n  ") is None


def test_returns_none_on_malformed_output() -> None:
    raw = "I cannot help with that question."
    assert parse_response(raw) is None


def test_rejects_mutating_query_in_sql_tag() -> None:
    raw = "<sql>DELETE FROM users WHERE id = 1</sql>"
    assert parse_response(raw) is None


def test_rejects_mutating_query_in_fenced_block() -> None:
    raw = "```sql\nDROP TABLE customers\n```"
    assert parse_response(raw) is None


def test_rejects_update_query() -> None:
    raw = "UPDATE orders SET status = 'shipped'"
    assert parse_response(raw) is None


def test_handles_multiline_sql_inside_tag() -> None:
    raw = """<sql>
    SELECT o.id, c.name
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    </sql>"""
    result = parse_response(raw)
    assert result is not None
    assert "JOIN customers" in result.query


def test_first_valid_candidate_wins_when_multiple_tags() -> None:
    raw = "<sql>SELECT 1</sql><sql>SELECT 2</sql>"
    result = parse_response(raw)
    assert result is not None
    assert result.query == "SELECT 1"


def test_skips_mutating_candidate_and_picks_valid_one() -> None:
    raw = "<sql>DROP TABLE x</sql><sql>SELECT 1</sql>"
    result = parse_response(raw)
    assert result is not None
    assert result.query == "SELECT 1"
