# RootLens: Self-Healing AI Log Analysis System

RootLens is a self-healing AI system designed to ingest large-scale application logs in real-time, group recurring issues via vector similarity clustering, run root-cause analysis (RCA) leveraging a Large Language Model (LLM), and trigger automated remediation actions to restore service health.

---

## 🚀 Key Features

* **Real-time Log Ingestion**: High-performance FastAPI endpoints built to accept and validate log streams using Pydantic.
* **Asynchronous Ingest Pipelines**: Immediately response to API log ingestion requests and offload heavy workloads to Celery and Redis.
* **Log Embedding Service**: Convert log messages into dense 384-dimensional semantic vectors using `sentence-transformers` (`BAAI/bge-small-en-v1.5`) with GPU/Apple Silicon acceleration.
* **Vector Search Database**: Index and query logs and payloads with Qdrant vector database to perform semantic similarity matches.
* **Incident Resolution**: Automatically group similar logs and map them to their corresponding SQL database incidents to return top 10 relevant occurrences.
* **Self-Healing Remediation**: Define and dispatch automated scripts or webhooks to resolve recurring issues autonomously.
* **Modern Web Dashboard**: Visual interface to monitor ingestion rates, active incident clusters, LLM explanations, and recovery statuses.

---

## 🛠️ Architecture & Pipeline

```mermaid
flowchart TD
    A[Log Generators] -->|HTTP POST| B(FastAPI Log Ingestor)
    B -->|Save Raw Log| C[(SQL Database)]
    B -->|Dispatch Task| D{Redis Message Queue}
    D -->|Consume Task| E[Celery Background Worker]
    E -->|1. Fetch Log| C
    E -->|2. Generate Embeddings| F(LogEmbeddingService)
    E -->|3. Index Vector + Payload| G[(Qdrant Vector DB)]
    G -->|4. Resolve Top 10 Incidents| H[Dashboard UI]
```

1. **Log Collection**: Microservices and systems send logs to the API.
2. **Ingestion & Validation**: FastAPI processes inputs, validating schemas against Pydantic models.
3. **Queue & Dispatch**: API saves the log and pushes a background task to the Redis broker, returning success immediately.
4. **Embedding Generation**: The Celery worker picks up the task and uses `sentence-transformers` to generate the log embedding vector.
5. **Vector Indexing**: Worker indexes the log metadata and vector representation in Qdrant.
6. **Incident Search**: Users or services query similar logs, resolving unique parent incidents ordered by semantic score.

---

## 📁 Repository Structure

```text
RootLens/
├── alembic/                # Database migrations history and environment
├── alembic.ini             # Alembic configuration
├── app/
│   ├── api/
│   │   └── logs.py         # Log ingestion endpoint routes
│   ├── services/
│   │   ├── embeddings.py   # Model loading and embedding vector service
│   │   └── vector_store.py # Qdrant client, indexing, and semantic search
│   ├── celery_app.py       # Celery worker application configuration
│   ├── config.py           # Configuration loading via pydantic-settings
│   ├── database.py         # SQLAlchemy engine and session setup
│   ├── main.py             # FastAPI bootstrapping entrypoint
│   ├── models.py           # SQLAlchemy schemas (Logs, Clusters, Incidents)
│   ├── schemas.py          # Pydantic validation schemas
│   └── tasks.py            # Celery tasks definitions (log processing)
├── requirements.txt        # Python project dependencies
├── test_ingestion.py       # Log API ingestion verification script
├── test_models.py          # Database relationship validation script
├── test_embeddings.py      # Embedding generation and similarity validation
├── test_qdrant.py          # Qdrant indexing and incident resolution validation
└── test_async.py           # Celery background processing integration test
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
Ensure you have **Python 3.9+** and a running **Redis** server (for production async queueing) installed on your system.

### 2. Environment Setup
Clone the repository and create a Python virtual environment:
```bash
# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment (macOS/Linux)
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Database Migrations
Configure your database connection URL (defaults to a local SQLite database `rootlens.db` for easy development if no `DATABASE_URL` is set). Run the migrations:
```bash
# Apply migrations to build the tables (logs, clusters, incidents)
alembic upgrade head
```

---

## 🧪 Testing and Verification

You can verify each system module individually using the test suites:

### 1. Model Relationships Test
Verifies the database constraints, relationships (Incident -> Cluster -> Log), and cascade delete behaviors:
```bash
python test_models.py
```

### 2. Embedding Service Test
Verifies model loading, device hardware acceleration detection (`cuda`/`mps`/`cpu`), single and batch embedding, and cosine similarity calculations:
```bash
python test_embeddings.py
```

### 3. Qdrant Integration Test
Verifies database persistence, embedding indexing in Qdrant (runs in-memory via `:memory:` by default), and semantic queries resolving to top relevant SQL incidents:
```bash
python test_qdrant.py
```

### 4. Background Async Pipeline Test
Verifies the end-to-end background ingestion flow using FastAPI's `TestClient` and Celery eager execution (executes tasks in-thread for testing):
```bash
python test_async.py
```

---

## ⚙️ Production Deployment

In a production environment, override the default settings using environment variables (or a `.env` file):

1. **Start Qdrant & Redis Services** (e.g., using Docker):
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   docker run -p 6379:6379 redis:latest
   ```

2. **Configure App Variables**:
   Create a `.env` file in the root directory:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/rootlens
   QDRANT_URL=http://localhost:6333
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   CELERY_ALWAYS_EAGER=False
   ```

3. **Start the Celery Background Worker**:
   ```bash
   celery -A app.celery_app worker --loglevel=info
   ```

4. **Start the FastAPI Web Server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
