# nl2sql

[![CI Status](https://github.com/Nahyan04/nl2sql/actions/workflows/ci.yml/badge.svg)](https://github.com/Nahyan04/nl2sql/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)

A FastAPI service that turns a natural language question into a validated, read-only SQL query, checked against a live PostgreSQL schema. I built it to show a complete nl2sql pipeline: schema introspection, retrieval, prompting a local LLM, and SQL validation.

## Architecture

```text
                         +-------------------------+
                         |   POST /api/v1/query    |
                         +------------+------------+
                                      |
                                      v
                         +-------------------------+
                         |   Schema Introspector   |
                         +------------+------------+
                                      |
                                      v
       +---------------------------------------------------------------+
       |                       Retrieval Pipeline                      |
       |  1. Lexical Scoring (tables, columns, domain aliases)         |
       |  2. Foreign Key Expansion (1-hop neighbors for join context)  |
       |  3. Optional Embedding Rerank (in-memory cosine similarity)   |
       +------------------------------+--------------------------------+
                                      |
                                      v
                         +-------------------------+
                         |     Prompt Builder      |
                         +------------+------------+
                                      |
                                      v
                         +-------------------------+
                         | Pluggable LLM Provider  |
                         |    (Ollama / Qwen2.5)   |
                         +------------+------------+
                                      |
                                      v
                         +-------------------------+
                         |  sqlglot AST Validator  | <---+ (Retry loop if invalid, max 3)
                         +------------+------------+     |
                                      |                  |
                            ( Valid Read-Only SQL )      |
                                      |                  |
                                      v                  |
                         +-------------------------+     |
                         |  Validated SQL Response |-----+
                         +-------------------------+
```

## How it works

1. Introspect the connected Postgres database's schema (tables, columns, foreign keys) at request time.
2. Score tables against the question using lexical matching (table/column names, plus an optional alias file for domain synonyms like `purchases -> orders`).
3. Expand the shortlist with foreign-key neighbors so joins are easier for the model to get right.
4. Optionally rerank the shortlist with embeddings.
5. Serialize the selected tables into a compact schema description and prompt a local LLM for SQL.
6. Parse the response, reject anything that isn't a read-only `SELECT`/`WITH` query (via `sqlglot`), and retry up to 3 times on failure.

No vector database. The schema is small enough that in-memory lexical scoring plus optional embedding reranking covers it, and it keeps the project simple to clone and run.

## Tech stack

- Python 3.11, FastAPI, Pydantic Settings
- SQLAlchemy + PostgreSQL
- Ollama (local LLM, pluggable)
- `sqlglot` for read-only SQL validation
- Docker / Docker Compose
- pytest

## Setup (Docker, recommended)

1. Install [Ollama](https://ollama.com) and pull a model e.g.:
   ```bash
   ollama pull qwen2.5-coder:7b
   ```
   Make sure Ollama is running (`ollama serve`, or just have the Ollama app open). It needs to be reachable from the container.

2. Copy the env file and adjust if needed:
   ```bash
   cp .env.example .env
   ```
   `LLM_BASE_URL` defaults to `http://host.docker.internal:11434`, which is how the app container reaches Ollama running on your host machine (works on Docker Desktop for Mac/Windows; `docker-compose.yml` also adds the `host-gateway` mapping so it works on Linux).

3. Start everything:
   ```bash
   docker compose up
   ```
   This brings up Postgres and the API (with hot reload) on `http://localhost:8000`.

4. Seed the demo data (see below) and you're ready to query.

## Setup (without Docker)

Requires a Postgres instance already running.

```bash
pip install -r requirements.txt
cp .env.example .env   # set DATABASE_URL and LLM_BASE_URL=http://localhost:11434
python scripts/check_db.py   # verify DB connectivity
uvicorn app.main:app --reload
```

## Demo data

`scripts/seed_demo_db.py` creates a small e-commerce schema (`customers`, `products`, `orders`, `order_items`) and seeds it with sample rows.

```bash
docker compose exec app python scripts/seed_demo_db.py
```

Then ask it something:

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Which customers have spent the most money in total?"}'
```

```json
{
  "query": "SELECT c.id, c.name, SUM(oi.quantity * oi.unit_price) AS total_spent\nFROM customers c\nJOIN orders o ON o.customer_id = c.id\nJOIN order_items oi ON oi.order_id = o.id\nGROUP BY c.id, c.name\nORDER BY total_spent DESC",
  "tables_used": ["customers", "order_items", "orders", "products"],
  "explanation": "",
  "is_valid": true,
  "explain_plan": null
}
```

## API

| Endpoint | Description |
|---|---|
| `GET /health` | Checks the app can reach the database |
| `GET /info` | Current provider, model, and retrieval config |
| `GET /api/v1/schema` | Full introspected schema |
| `GET /api/v1/schema/{table}` | Schema for a single table |
| `POST /api/v1/query` | Natural language question -> validated SQL |

`POST /api/v1/query` body:

```json
{
  "question": "How many orders are still pending?",
  "top_n_tables": 8,
  "dry_run": false
}
```

Set `"dry_run": true` to also run `EXPLAIN` on the generated query and return the plan, without executing it:

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top 3 best selling products by quantity sold?", "dry_run": true}'
```

## Switching to a cloud model provider

The service is provider-pluggable. `app/core/providers/base.py` defines `TextGenerationProvider` and `EmbeddingProvider` interfaces; `app/core/providers/ollama.py` is the only adapter implemented so far. To add a cloud provider (OpenAI-compatible endpoint, Gemini, etc.):

1. Implement `TextGenerationProvider` (and `EmbeddingProvider` if you want reranking) in a new file under `app/core/providers/`.
2. Register it in `get_text_provider`/`get_embedding_provider` in `app/core/providers/__init__.py`.
3. Set `LLM_PROVIDER` (and `EMBEDDING_PROVIDER`) in `.env` to your new provider's name.

The pipeline itself never imports a specific provider directly, so this is the only wiring needed.

## Environment variables

See `.env.example` for the full list. The important ones:

- `DATABASE_URL` — Postgres connection string
- `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL` — text generation provider
- `EMBEDDING_ENABLED`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL` — optional reranking
- `SCHEMA_ALIAS_PATH` — path to a JSON file mapping domain terms to table names (see `app/resources/schema_aliases.example.json`)

## Running tests

```bash
docker compose run --rm -v "$(pwd)/tests:/app/tests" app pytest
```

Unit tests use in-memory SQLite and mocked providers; integration tests exercise the full pipeline and API layer against a shared SQLite fixture.

## Project structure

```text
nl2sql/
├── app/
│   ├── api/routes/     — query, schema, health, info endpoints
│   ├── core/           — db engine, providers, prompt builder, logging, aliases
│   ├── models/         — Pydantic request/response models
│   ├── resources/      — schema alias example file
│   └── services/
│       └── retrieval/  — lexical scoring, FK expansion, embedding rerank
├── scripts/            — DB connectivity check, demo data seeding
├── tests/
│   ├── integration/
│   └── unit/
├── .env.example
├── docker-compose.yml
└── requirements.txt
```

## Known limitations

- A local 7-9B model can still produce logically incorrect SQL even when it's syntactically valid.
- `dry_run` uses `EXPLAIN`, not `EXPLAIN ANALYZE`, so no queries are actually executed.
- No authentication layer.
- No vector database. Retrieval is lexical plus optional in-memory embedding reranking, which is enough for a schema this size.

## License

This project is licensed under the [MIT License](LICENSE).

