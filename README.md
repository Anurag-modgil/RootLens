# RootLens: Self-Healing AI Log Analysis System

RootLens is a self-healing AI system designed to ingest large-scale application logs in real-time, group recurring issues via vector similarity clustering, run root-cause analysis (RCA) leveraging a Large Language Model (LLM), and trigger automated remediation actions to restore service health.

---

## 🚀 Key Features

* **Real-time Log Ingestion**: High-performance FastAPI endpoints built to accept and validate log streams using Pydantic.
* **Intelligent Clustering**: Convert raw logs into high-dimensional vectors to cluster recurring problems.
* **LLM Root-Cause Engine**: Produce human-readable diagnosis reports detailing exactly why a failure occurred.
* **Self-Healing Remediation**: Define and dispatch automated scripts or webhooks to resolve recurring issues autonomously.
* **Modern Web Dashboard**: Visual interface to monitor ingestion rates, active incident clusters, LLM explanations, and recovery statuses.

---

## 🛠️ Architecture & Pipeline

```mermaid
flowchart LR
    A[Log Generators] -->|HTTP POST| B(FastAPI Log Ingestor)
    B -->|Database Session| C[(PostgreSQL DB)]
    C -->|Asynchronous Worker| D(Embedding & Clustering)
    D -->|Issue Clusters| E(LLM Root-Cause Engine)
    E -->|Remediation Proposal| F(Remediation Dispatcher)
    F -->|Recovery Scripts / Webhooks| G[Self-Healed Services]
```

1. **Log Collection**: Microservices and systems send logs to the API.
2. **Ingestion & Validation**: FastAPI processes inputs, validating schemas against Pydantic models.
3. **Clustering & Embeddings**: Asynchronous pipelines translate text into vectors to detect recurring issues.
4. **Root-Cause Analysis**: An LLM-backed agent inspects log groups to generate human-readable reports.
5. **Remediation**: Actions (e.g. system reboots, disk cleanups, webhooks) are executed to fix issues automatically.

---

## 📁 Repository Structure

```text
RootLens/
├── alembic/                # Database migrations history and environment
├── alembic.ini             # Alembic configuration
├── app/
│   ├── api/
│   │   └── logs.py         # Log ingestion endpoint routes
│   ├── config.py           # Configuration loading via pydantic-settings
│   ├── database.py         # SQLAlchemy engine and session setup
│   ├── main.py             # FastAPI bootstrapping entrypoint
│   ├── models.py           # SQLAlchemy schemas (Logs, Clusters, Incidents)
│   └── schemas.py          # Pydantic validation schemas
├── requirements.txt        # Python project dependencies
├── test_ingestion.py       # Log API ingestion verification script
└── test_models.py          # Database relationship validation script
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
Ensure you have **Python 3.9+** installed on your system.

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

To verify that the ingestion endpoints and database schemas are fully operational:

### Run Model Relationships Test
This script verifies the creation of logs, clusters, and incidents, validating database relationships and cascade delete configurations:
```bash
python test_models.py
```

### Run Log Ingestion Endpoint Test
1. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```
2. In a separate terminal shell, execute the log ingestion test script:
   ```bash
   python test_ingestion.py
   ```
   You should receive a `201 Created` response containing the validated log metadata and confirmation of db persistence.
