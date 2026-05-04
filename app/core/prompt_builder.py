from __future__ import annotations

# Rough character ceiling for the combined system + user prompt.
# Local 7-9B models typically have a 4096-8192 token context; ~6000 chars is a safe budget.
MAX_PROMPT_CHARS = 6000

_SYSTEM_PROMPT = """\
You are a SQL generation assistant for a PostgreSQL database.

Rules:
- Only generate SELECT or WITH (CTE) queries. Never write INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, or any other mutating statement.
- Use standard PostgreSQL syntax.
- Output your final SQL query wrapped in <sql> and </sql> tags, with no other text inside those tags.
- If you cannot answer the question from the provided schema, reply with <sql>-- cannot answer</sql>.

Examples:

Question: Show customers who placed more than 5 orders.
<sql>
SELECT c.id, c.name, COUNT(o.id) AS order_count
FROM customers c
JOIN orders o ON o.customer_id = c.id
GROUP BY c.id, c.name
HAVING COUNT(o.id) > 5;
</sql>

Question: List products in the "Electronics" category that are still in stock.
<sql>
SELECT id, name, price, stock_qty
FROM products
WHERE category = 'Electronics'
  AND stock_qty > 0;
</sql>
"""


def build_system_prompt() -> str:
    return _SYSTEM_PROMPT


def build_user_prompt(question: str, schema_context: str) -> str:
    prompt = f"Schema:\n{schema_context}\n\nQuestion: {question}"
    # Trim combined length to stay within budget (system prompt is ~fixed overhead).
    system_len = len(_SYSTEM_PROMPT)
    available = MAX_PROMPT_CHARS - system_len
    if len(prompt) > available:
        prompt = prompt[:available]
    return prompt
