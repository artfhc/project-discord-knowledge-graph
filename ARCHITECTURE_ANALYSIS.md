# Architecture Analysis & Recommendations

## Overview

This document provides architectural recommendations for the Discord Knowledge Graph Pipeline project, evaluating different approaches including microservices, monolithic architecture, and workflow orchestration options.

## Current Requirements Analysis

Based on the PRD, the system needs:
- **3-layer pipeline**: Ingestion → Preprocessing → Entity/Relation Extraction
- **Discord API integration** for historical message fetching
- **LLM-based processing** for classification and triple extraction
- **Knowledge graph storage** for structured relationships
- **Scheduled execution** via cron jobs
- **Scalable processing** for large message volumes

## Architecture Options Evaluated

### 1. Microservices Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Ingestion   │ →  │Preprocessing│ →  │ Extraction  │
│ Service     │    │ Service     │    │ Service     │
│ (discord.py)│    │ (LLM calls) │    │ (LLM calls) │
└─────────────┘    └─────────────┘    └─────────────┘
```

**Pros:**
- Independent scaling per service
- Technology flexibility per layer
- Independent deployments
- Clear service boundaries

**Cons:**
- Higher operational complexity
- Network latency between services
- Distributed debugging challenges
- Premature for single-developer project
- No clear scaling bottlenecks identified yet

**Recommendation:** Not recommended for initial implementation.

### 2. Monolithic Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                   Discord KG Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Ingestion │→ │Preprocessing│→ │ Extraction  │        │
│  │   Module    │  │   Module    │  │   Module    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                   Shared Components                         │
│  • Database Layer • LLM Client • Config • Logging          │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- Single deployment/debugging surface
- Shared database transactions
- Faster iteration during development
- Lower operational complexity
- Easy to profile end-to-end performance
- Simple state management

**Cons:**
- Single point of failure
- Coupled scaling requirements
- Technology lock-in

**Recommendation:** Ideal starting point.

### 3. N8N Workflow Orchestration

**Evaluation:**

**Good for:**
- Visual pipeline management
- Easy retry/error handling
- Built-in scheduling
- No-code pipeline modifications
- Webhook integrations

**Challenges for this use case:**
- Custom Python logic (discord.py, LLM calls) requires custom nodes
- Bulk data processing may hit n8n execution limits
- Less control over performance optimization
- Additional infrastructure dependency
- Complex data transformations better handled in code

**Recommendation:** Consider for orchestration layer only, not core processing.

## Recommended Architecture

### Hybrid Monolith-First with Orchestration Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                        │
│    Cron/Airflow/n8n → Trigger Pipeline → Monitor Progress       │
└─────────────────────────────────────────────────────────────────┘
                                     │
┌─────────────────────────────────────────────────────────────────┐
│                    CORE PIPELINE (Monolith)                     │
├─────────────────────────────────────────────────────────────────┤
│  Discord API → Raw Messages → Message Queue → Processing        │
│                                     │                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Ingestion   │ →  │Preprocessing│ →  │ Extraction  │        │
│  │ - Fetch API │    │ - Clean     │    │ - LLM Calls │        │
│  │ - Paginate  │    │ - Classify  │    │ - Generate  │        │
│  │ - Store Raw │    │ - Segment   │    │   Triples   │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                                     │
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                              │
│  Raw Messages DB → Processed Messages → Knowledge Graph DB      │
│  (PostgreSQL)        (PostgreSQL)        (Neo4j/PostgreSQL)    │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Separation of Concerns**
   - Orchestration handles scheduling and monitoring
   - Core pipeline focuses on data processing
   - Storage layer manages persistence and querying

2. **Staged Processing**
   - Raw message storage for reprocessability
   - Intermediate processed message storage
   - Final knowledge graph storage

3. **Streaming Pipeline**
   - Process messages in configurable batches
   - Handle backpressure gracefully
   - Support incremental processing

4. **Queue-Based Flow**
   - Decouple processing stages
   - Enable retry mechanisms
   - Handle failures gracefully

## Technology Stack Recommendations

### Phase 1: MVP Implementation
- **Core Pipeline:** Python monolith
- **Web Framework:** FastAPI (for monitoring/health endpoints)
- **Orchestration:** Cron jobs with simple scheduling
- **Primary Database:** PostgreSQL
- **Knowledge Graph:** PostgreSQL with graph extensions or separate Neo4j
- **Message Queue:** In-memory queues initially
- **LLM Integration:** OpenAI API or local model via Ollama

### Phase 2: Production Scaling
- **Orchestration:** Airflow or n8n for complex workflows
- **Message Queue:** Redis or RabbitMQ
- **Monitoring:** Prometheus + Grafana
- **Containerization:** Docker with docker-compose
- **CI/CD:** GitHub Actions

### Phase 3: Advanced Scaling (if needed)
- **Split into microservices** based on actual bottlenecks
- **Kubernetes deployment** for orchestration
- **Event-driven architecture** with Apache Kafka
- **Distributed knowledge graph** with cluster setup

## Migration Strategy

### When to Consider Microservices Split

**Triggers for migration:**
- API rate limit issues requiring different scaling patterns
- Multiple teams needing independent deployments  
- Clear performance bottlenecks in specific layers
- Different technology requirements per service

**Suggested split points:**
1. **Ingestion Service** - If Discord API limits require specialized handling
2. **LLM Processing Service** - If GPU requirements differ from other components
3. **Graph Storage Service** - If query patterns require specialized optimization

### Implementation Phases

**Phase 1: Monolithic MVP (Weeks 1-4)**
- Single Python application
- Basic cron scheduling
- PostgreSQL storage
- Simple monitoring

**Phase 2: Enhanced Orchestration (Weeks 5-8)**
- Add proper workflow orchestration
- Implement robust error handling
- Add monitoring and alerting
- Optimize batch processing

**Phase 3: Selective Scaling (Month 3+)**
- Profile performance bottlenecks
- Split services only where necessary
- Implement proper service mesh if microservices route chosen

## Conclusion

**Start with a monolithic pipeline** for rapid development and iteration. The architecture should be designed with clear module boundaries that allow for future microservice extraction if needed. Focus on solving the core problem first, then optimize based on real usage patterns and bottlenecks.

The hybrid approach provides the best balance of development velocity, operational simplicity, and future scalability options.