# Discord Knowledge Graph Pipeline

A system that ingests messages from Discord servers, processes and classifies them, extracts semantic relationships as structured triples, and stores them in a knowledge graph for LLM integration.

## Architecture

The system follows a 3-layer pipeline:
1. **Ingestion**: Fetches Discord messages and stores raw data in Backblaze B2
2. **Preprocessing**: Cleans and classifies messages using LLM
3. **Extraction**: Generates knowledge graph triples and stores in Neo4j

## Project Structure

```
src/discord_kg/
├── ingestion/          # Discord API fetching and B2 storage
├── preprocessing/      # Message cleaning and classification  
├── extraction/         # Triple extraction from messages
├── storage/           # Neo4j and PostgreSQL clients
├── web/               # FastAPI + Streamlit interfaces
└── utils/             # Config, logging, shared utilities

scripts/               # Execution and setup scripts
config/               # Configuration files
tests/                # Test modules
```

## Quick Start

### 1. Setup Environment

```bash
# Clone and setup
git clone <repository>
cd project-discord-knowledge-graph

# Install dependencies
pip install -r requirements.txt
# OR with pyproject.toml
pip install -e .

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

### 2. Configure Services

**Required credentials:**
- Discord Bot Token
- OpenAI API Key  
- Neo4j Aura connection details
- Backblaze B2 credentials
- PostgreSQL connection string (Render managed)

### 3. Database Setup

```bash
# Test connections and create tables
python scripts/setup_db.py --test-connections --create-tables
```

### 4. Run Pipeline

```bash
# Full pipeline
python scripts/run_pipeline.py --full

# Individual phases
python scripts/run_pipeline.py --ingest-only
python scripts/run_pipeline.py --process-only
```

### 5. Start Web Interface

```bash
# Both API and Streamlit
python scripts/start_web.py

# Individual services
python scripts/start_web.py --api-only
python scripts/start_web.py --streamlit-only
```

## Deployment (Render)

### Web Service
- Deploy FastAPI + Streamlit from this repository
- Set environment variables in Render dashboard
- Auto-deploys on git push

### Cron Job
- Separate Render service for scheduled pipeline execution
- Configure build command: `pip install -r requirements.txt`
- Configure start command: `python scripts/run_pipeline.py --full`

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Code formatting
black src/ scripts/ tests/
isort src/ scripts/ tests/

# Linting
flake8 src/ scripts/ tests/

# Testing
pytest tests/
```

## Key Components

### Ingestion (`src/discord_kg/ingestion/`)
- **DiscordIngestor**: Fetches messages via Discord API
- **B2Storage**: Stores raw JSON in partitioned structure

### Preprocessing (`src/discord_kg/preprocessing/`)
- **MessageCleaner**: Normalizes message content
- **MessageClassifier**: LLM-based classification (question/answer/alert/strategy)

### Extraction (`src/discord_kg/extraction/`)  
- **TripleExtractor**: Generates (subject, predicate, object) triples

### Storage (`src/discord_kg/storage/`)
- **Neo4jClient**: Knowledge graph operations
- **PostgresClient**: Processing state and metadata

### Web (`src/discord_kg/web/`)
- **FastAPI**: REST API for queries and stats
- **Streamlit**: Visual interface and graph exploration

## Configuration

All settings managed via `src/discord_kg/utils/config.py` using Pydantic Settings:
- Environment variables from `.env` file
- Validation and type checking
- Default values for optional settings

## Tech Stack

- **Language**: Python 3.9+
- **Discord API**: discord.py
- **LLM**: OpenAI API + LangChain  
- **Graph DB**: Neo4j Aura
- **Relational DB**: PostgreSQL (Render managed)
- **Object Storage**: Backblaze B2
- **Web**: FastAPI + Streamlit
- **Hosting**: Render (web services + cron jobs)

## License

MIT License - see LICENSE file
