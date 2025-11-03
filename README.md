# Logiq

Logiq is an open-source, self-hostable backend that ingests raw application logs and lets developers interrogate them with natural language. Instead of wrestling with ad-hoc regex or proprietary query languages, engineers can speak to their logs and receive concise, contextual answers powered by a Retrieval-Augmented Generation (RAG) pipeline.

## Features

- **Fast ingestion**: `/ingest` accepts JSON payloads and queues processing instantly (<50 ms target).
- **Semantic retrieval**: Logs are embedded with Sentence-Transformers and stored in PostgreSQL + pgvector for similarity search.
- **LLM-backed answers**: `/query` transforms questions into embeddings, retrieves relevant logs, and synthesizes responses with a configurable open-source model (Gemma 2 2B by default).
- **Containerised stack**: FastAPI API, Celery workers, PostgreSQL, and Redis orchestrated via Docker Compose.

## Architecture

- `api`: FastAPI service exposing REST endpoints.
- `worker`: Celery worker handling embeddings + persistence asynchronously.
- `db`: PostgreSQL (with pgvector extension) storing structured logs & vectors.
- `redis`: Message broker/result backend for Celery.
- `models/`: Mount point where you place your local GGUF model (for `llama-cpp-python`).

More design details live in `docs/architecture.md`.

## Getting Started

### 1. Prerequisites

- Docker & Docker Compose
- Internet access for first-time model downloads (`sentence-transformers`)
- A GGUF model file for the LLM (the default Compose setup looks for `./models/gemma2-2b-logiq.gguf`)

### 2. Environment Configuration

Create a `.env` file (optional) to override defaults:

```
DATABASE_URL=postgresql+psycopg2://logiq:logiq@db:5432/logiq
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
LLM_MODEL_PATH=/models/gemma2-2b-logiq.gguf
LLM_N_CTX=4096
LLM_N_THREADS=0
LLM_N_GPU_LAYERS=0
LLM_BATCH_SIZE=512
LLM_TEMPERATURE=0.1
LLM_TOP_P=0.9
RETRIEVAL_TOP_K=5
MAX_CONTEXT_LOGS=10
LOGIQ_LOG_LEVEL=INFO
```

> The compose file already exports sensible defaults; the `.env` file lets you customise them across services.

### 3. Start the Stack

```
docker compose up --build
```

This builds the shared Python image and launches the following containers:

- `logiq-api`: FastAPI application on `http://localhost:8000`
- `logiq-worker`: Celery worker consuming ingestion tasks
- `logiq-db`: PostgreSQL with pgvector extension
- `logiq-redis`: Redis broker

The first run downloads the embedding model; subsequent runs reuse the cached copy inside the image.

### 4. Explore the API

- Open http://localhost:8000/docs for interactive Swagger UI.
- Health check: `curl http://localhost:8000/healthz`.

#### Ingest Logs

```
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "service": "auth-api",
        "level": "ERROR",
        "message": "User 501 failed login",
        "log_timestamp": "2024-05-10T12:34:56Z",
        "ip": "10.12.0.15",
        "attributes": {"user_id": 501}
      }'
```

Returns immediately with a task id:

```
{"status":"accepted","task_id":"..."}
```

#### Query Logs

```
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
        "query": "show me login failures for auth-api",
        "filters": {"service": "auth-api"},
        "limit": 5
      }'
```

Response:

```
{
  "answer": "...",
  "logs": [...],
  "contexts": [...],
  "requested_k": 5,
  "used_k": 3
}
```

If the LLM model is not configured, Logiq gracefully falls back to returning the matching log messages verbatim.

### Integrating with Existing Systems

You can adopt Logiq as a stand-alone service or embed individual components inside a Python monorepo:

- **REST ingestion/query** (recommended): Point your applications at `/ingest` and `/query`. Both endpoints accept/return JSON, so you can drop them behind an internal load balancer and start publishing logs immediately.
- **Publish directly to Celery**: Import `process_log` from `app.tasks` and call `process_log.delay({...})` if you already operate a Celery-compatible broker. Use the same payload schema as the `/ingest` endpoint.
- **Embed the pipeline**: Import `RAGPipeline` (`app/services/rag.py`) for in-process natural-language queries. Combine it with `get_db_session()` to run queries without HTTP.

### Using Gemma 2 2B from Ollama

1. Pull the model with Ollama (example for the instruct variant):

   ```
   ollama pull gemma2:2b
   ```

2. Identify the downloaded GGUF blob:

   ```
   ollama show gemma2:2b --modelfile | grep FROM
   ```

   The output contains a blob path similar to `./blobs/sha256-<hash>`. The full file lives under
   `~/.ollama/models/blobs/sha256-<hash>`.

3. Copy or symlink the blob into Logiq's `models/` directory:

   ```
   mkdir -p models
   cp ~/.ollama/models/blobs/sha256-<hash> models/gemma2-2b-logiq.gguf
   ```

4. Update `.env` (or your Compose overrides) so the services load the file and broaden the context window for the larger model:

   ```
   LLM_MODEL_PATH=/models/gemma2-2b-logiq.gguf
   LLM_N_CTX=4096
   LLM_BATCH_SIZE=512
   LLM_N_THREADS=$(sysctl -n hw.logicalcpu)  # adjust for your machine
   # Optional, if you have GPU acceleration available via llama.cpp builds:
   # LLM_N_GPU_LAYERS=20
   ```

5. Restart the containers (`docker compose restart api worker`). The first query will take a moment while the model warms up; subsequent requests reuse the loaded weights.

> Tip: Quantized variants (`q4_k_m`, `q5_k_m`, etc.) offer the best CPU-only experience. If you notice context overflow errors, increase `LLM_N_CTX` or reduce request complexity.

## Development Workflow

- The `api` service hot-reloads thanks to the mounted project directory.
- Celery reloads code by recreating the container (`docker compose restart worker`).
- Run arbitrary commands inside the API container: `docker compose exec api bash`.

## Testing

Future work will add automated tests for ingestion, vector retrieval and prompt assembly. For now you can:

- Inspect Celery logs (`docker compose logs -f worker`).
- Connect to Postgres (`docker compose exec db psql -U logiq -d logiq`) and query the `logs` table.

## Troubleshooting

- **LLM file missing**: Ensure `LLM_MODEL_PATH` points to a file inside `./models`. Without it, Logiq returns the fallback answer.
- **Slow first request**: The embedding model is loaded lazily on first use; subsequent requests are fast.
- **Database errors on startup**: Double-check Docker Compose has started `logiq-db`. The worker retries automatically if the DB is still booting.

## Roadmap

- Authentication & multi-tenancy
- Advanced filtering (e.g., boolean expressions, aggregation dashboards)
- Automated evaluation harness for relevance & latency
- Observability (metrics, tracing) for ingestion pipeline

Contributions and feedback are welcome!
