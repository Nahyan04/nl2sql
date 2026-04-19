# nl2sql

`nl2sql` is a local-first FastAPI service that turns natural language questions into SQL grounded in a live database schema.

The repo is being built as a POC: practical to demonstrate sound retrieval, prompt, and safety decisions.

## Why This Approach

A lot of NL2SQL demos stop at one of two weak extremes:

- dump the whole schema into the prompt and hope the model figures it out
- introduce a full vector database before the problem size actually justifies it

This project takes a better middle path:

- introspect the schema live
- build a compact schema catalog
- shortlist relevant tables with deterministic lexical scoring
- expand context through foreign-key relationships
- optionally rerank the shortlist with embeddings
- pass only the final compressed context to the LLM

That keeps the system explainable, testable, and strong enough to showcase architectural judgment.

## Why No Vector DB in v1

This is a deliberate choice, not a missing feature.

- Most application schemas are small enough that table-level retrieval can stay in memory.
- The retrieval target is schema metadata, not millions of documents.
- Optional embedding reranking over a small shortlist gets most of the semantic benefit without extra infrastructure.
- Avoiding a vector database keeps the repo easier to run, review, and modify after cloning.

If the project later grows, a vector store can be introduced behind the same retriever abstraction.

## Retrieval Strategy

The current architecture direction:

1. Introspect PostgreSQL schema metadata into a normalized catalog.
2. Build a text descriptor for each table from names, columns, and FK relationships.
3. Score the schema lexically to get a deterministic shortlist.
4. Expand the shortlist with direct FK neighbors so joins are easier for the model to infer.
5. Optionally rerank the shortlist with embeddings cached in memory.
6. Serialize the selected schema subset into a compact prompt context.

This is intentionally hybrid:

- lexical retrieval gives predictable baseline behavior
- relationship expansion improves multi-table coverage
- semantic reranking is optional, not mandatory infrastructure

## Provider Strategy

The runtime is local-first, but not hardwired forever.

- `Ollama` is the default text-generation provider for v1
- the codebase is being structured around provider interfaces for text generation and embeddings
- future adapters allow for OpenAI-compatible endpoints, Gemini, or other providers without rewriting the pipeline

That makes the repo useful both as a local demo and as a starting point for people who want to swap in their own model stack.

## Tech Stack

- Python 3.12+
- FastAPI
- Pydantic Settings
- SQLAlchemy
- PostgreSQL
- Ollama
- Docker / Docker Compose
- `httpx`
- `sqlglot`
- `pytest`

## Current Status

The implementation is still in progress.

## Environment Variables

The current scaffold uses these keys:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres

LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=qwen3.5:9b

EMBEDDING_ENABLED=false
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text

RETRIEVAL_MODE=hybrid
SCHEMA_ALIAS_PATH=app/resources/schema_aliases.example.json
```

## Project Structure

```text
nl2sql/
├── app/
│   ├── api/
│   │   └── routes/
│   ├── core/
│   │   └── providers/
│   ├── models/
│   ├── resources/
│   └── services/
│       └── retrieval/
├── scripts/
├── tests/
│   ├── integration/
│   └── unit/
├── .env.example
├── PLAN.md
├── README.md
└── requirements.txt
```

## What This Repo Should Demonstrate

- clean FastAPI service structure
- live schema introspection instead of hardcoded database metadata
- retrieval decisions that are stronger than naive keyword matching
- local-first AI integration without framework bloat
- safety and validation around generated SQL

## Planned Limitations

Even with hybrid retrieval, this stays a POC:

- semantic reranking is optional and limited to schema descriptors
- generated SQL can still be logically wrong even when syntactically valid
- no authentication or authorization layer is planned for v1
- no vector database is included in v1 because the schema search space is intentionally small
