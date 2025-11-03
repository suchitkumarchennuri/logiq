## Logiq Architecture Overview

### High-Level Components

- **FastAPI service (`api`)**: Exposes `/ingest` and `/query` endpoints, validates payloads, and enqueues asynchronous work.
- **Celery workers (`worker`)**: Consume ingestion tasks, generate embeddings, persist logs, and orchestrate RAG query execution.
- **PostgreSQL + pgvector (`db`)**: Stores structured log metadata alongside vector embeddings to enable semantic similarity search.
- **Redis (`redis`)**: Acts as the Celery broker and result backend, ensuring ingestion requests return immediately (<50 ms).
- **Embeddings service**: Wraps a Sentence-Transformer model to vectorize log messages and user questions.
- **LLM service**: Interfaces with an open-source GGUF LLM (via `llama-cpp-python`)—defaults to a lightweight 7B model but supports larger options such as Gemma 3 12B.

### Data Flow: Ingest

1. Client submits JSON payload to `/ingest`.
2. FastAPI validates the payload and pushes it to Celery (`process_log` task); API responds with `202 Accepted` without waiting for persistence.
3. Worker fetches task, ensures database schema + pgvector extension exist, generates an embedding for the log message, and writes the structured record + vector into `logs` table.

### Data Flow: Query

1. Client calls `/query` with a natural-language prompt and optional filters (service, level, time range, limit).
2. API computes an embedding for the query using the shared Sentence-Transformer model.
3. Postgres `pgvector` extension performs a similarity search (`<->` operator) to pull top-k relevant logs, applying filter clauses.
4. Retrieved logs + original question feed into the LLM service, which produces an answer and citations.
5. API returns JSON containing the synthesized answer, the logs selected as context, and metadata about the retrieval.

### Persistence Model (`logs` table)

- `id` (UUID)
- `created_at` (timestamp with time zone)
- `service` (text)
- `level` (text)
- `message` (text)
- `metadata` (JSONB)
- `embedding` (vector)

### Operational Considerations

- **Singleton model loaders**: Embedding + LLM services are instantiated once per process to avoid repeated heavy initialisation.
- **Configuration**: Managed by environment variables (e.g., `DATABASE_URL`, `REDIS_URL`, `EMBEDDING_MODEL_NAME`, `LLM_MODEL_PATH`, `LLM_N_CTX`, `LLM_N_THREADS`, `LLM_N_GPU_LAYERS`).
- **Containerisation**: A single Python base image shared by API and worker, parameterised by runtime command; compose file orchestrates all services.
- **Scalability**: Horizontal scale via additional worker replicas; Postgres indexing on `embedding` and structured columns; eventually add observability for queue depth and task latency.

### Future Enhancements

- Implement structured filtering and aggregations (e.g., faceted counts).
- Add authentication / multi-tenant support.
- Introduce retention policies and archival storage.
- Build automated evaluations for answer accuracy and latency regression.
