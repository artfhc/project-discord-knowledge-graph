# Discord Knowledge Graph Extractor Architecture

This document provides visual diagrams and explanations of the `extractor_langgraph.py` system architecture.

## System Overview

```mermaid
graph TD
    A[🤖 CLI Entry Point<br/>extractor_langgraph.py] --> B[Parse CLI Arguments]
    B --> C{Validation}
    C -->|✅ Pass| D[Optional Flags Processing]
    C -->|❌ Fail| E[Exit with Error]
    
    D --> F[LLM Call Recording Setup]
    F --> G[Create ExtractionWorkflow]
    G --> H[Run Processing Pipeline]
    H --> I[Generate Summary Report]
    
    subgraph "Optional Modes"
        D1[--estimate-tokens<br/>Token Analysis]
        D2[--dry-run<br/>Validation Only]
        D3[--skip-qa-linking<br/>Fast Mode]
    end
    
    D --> D1
    D --> D2
    D --> D3
```

## CLI Options Flow

```mermaid
graph LR
    A[CLI Arguments] --> B[Provider Selection]
    A --> C[Batch Configuration]
    A --> D[Message Type Filtering]
    A --> E[Processing Options]
    
    B --> B1[--provider openai/claude]
    B --> B2[--model specific-model]
    
    C --> C1[--batch-size 20<br/>Maximum batch size]
    C --> C2[Dynamic Token Adjustment]
    
    D --> D1[--extract-types<br/>question answer strategy]
    D --> D2[Process All Types<br/>Default]
    
    E --> E1[--skip-qa-linking<br/>Faster processing]
    E --> E2[--enable-checkpoints<br/>Resume capability]
    E --> E3[--log-level DEBUG<br/>Detailed logging]
```

## Data Processing Pipeline

```mermaid
graph TD
    A[📄 Input JSONL File<br/>Discord Messages] --> B[🔧 Preprocessing Node]
    B --> C[🏷️ Classification Node]
    C --> D[📊 Message Type Routing]
    
    D --> E1[❓ Question Extraction]
    D --> E2[💡 Strategy Extraction]  
    D --> E3[📈 Analysis Extraction]
    D --> E4[💬 Answer Extraction]
    D --> E5[🚨 Alert Extraction]
    D --> E6[📊 Performance Extraction]
    D --> E7[💭 Discussion Extraction]
    
    E1 --> F{Q&A Linking Enabled?}
    E2 --> G[🔗 Aggregation Node]
    E3 --> G
    E4 --> F
    E5 --> G
    E6 --> G
    E7 --> G
    
    F -->|Yes| H[🔗 Q&A Linking Node]
    F -->|No| G
    H --> G
    
    G --> I[💰 Cost Tracking Node]
    I --> J[📄 Output JSONL File<br/>Extracted Triples]
    
    style A fill:#e1f5fe
    style J fill:#e8f5e8
    style F fill:#fff3e0
    style H fill:#fce4ec
```

## Dynamic Batch Sizing Logic

```mermaid
graph TD
    A[Messages to Process] --> B[Estimate Tokens per Message]
    B --> C[Calculate Optimal Batch Size]
    C --> D{Compare with User Batch Size}
    
    D -->|Optimal < User| E[Use Optimal Size<br/>Token-limited]
    D -->|Optimal ≥ User| F[Use User Size<br/>User preference respected]
    
    E --> G[Log Adjustment]
    F --> H[Process Batch]
    G --> H
    
    H --> I[API Call with Batch]
    I --> J{More Messages?}
    J -->|Yes| A
    J -->|No| K[Complete]
    
    subgraph "Token Limits by Provider"
        L1[Claude: ~13,333 tokens/batch<br/>50k tokens/min ÷ 3]
        L2[OpenAI: ~30,000 tokens/batch<br/>90k tokens/min ÷ 3]
    end
```

## Q&A Linking Process (Simplified)

```mermaid
graph TD
    A[131 Questions<br/>1,939 Answers] --> B[Batch Questions<br/>3-6 per batch]
    
    B --> C[For Each Question Batch]
    C --> D[Filter Answers:<br/>1. Direct Replies<br/>2. Next 20 Chronological]
    
    D --> E[Question Batch<br/>+ 20 Filtered Answers]
    E --> F[🤖 LLM API Call<br/>Which answers match which questions?]
    
    F --> G[Extract Q&A Links<br/>question_id → answered_by → answer_id]
    G --> H{More Question Batches?}
    
    H -->|Yes| C
    H -->|No| I[Combine All Q&A Links]
    
    subgraph "Efficiency Improvement"
        J[Before: 5 questions × 1,939 answers<br/>= 500k tokens per batch]
        K[After: 6 questions × 20 answers<br/>= 5k tokens per batch]
        J --> K
    end
```

## LLM Recording & Monitoring

```mermaid
graph TD
    A[🔧 Enable Recording<br/>ENABLE_LLM_RECORDING=true] --> B[Monkey Patch LLM Providers]
    
    B --> C[Intercept All API Calls]
    C --> D[Record Call Metadata:<br/>• Timestamp<br/>• Provider/Model<br/>• Tokens & Cost<br/>• Success/Failure<br/>• Processing Time<br/>• Batch Size]
    
    D --> E[Store in SQLite Database<br/>llm_calls.db]
    E --> F[📊 Analysis Dashboard<br/>llm_evaluation_app.py]
    
    F --> G[Interactive Visualizations:<br/>• Cost Analysis<br/>• Success Rates<br/>• Token Usage<br/>• Batch Efficiency<br/>• Template Performance]
    
    subgraph "Dashboard Features"
        H1[📈 Cost Trends]
        H2[⚡ Performance Metrics]
        H3[🎯 Success Rates by Template]
        H4[📦 Batch Size Analysis]
        H5[🔍 Individual Call Details]
    end
    
    G --> H1
    G --> H2
    G --> H3
    G --> H4
    G --> H5
```

## Module Dependencies

```mermaid
graph TD
    A[extractor_langgraph.py<br/>CLI Entry Point] --> B[workflow.py<br/>LangGraph Orchestration]
    
    B --> C[nodes.py<br/>Processing Nodes]
    B --> D[workflow_state.py<br/>State Management]
    
    C --> E[llm_providers.py<br/>OpenAI/Claude APIs]
    C --> F[token_utils.py<br/>Dynamic Batching]
    C --> G[config.py<br/>Prompt Templates]
    
    A --> H[enable_recording.py<br/>LLM Call Monitoring]
    H --> I[llm_recorder.py<br/>Database Storage]
    I --> J[llm_evaluation_app.py<br/>Analysis Dashboard]
    
    style A fill:#ff9999
    style B fill:#99ccff
    style E fill:#99ff99
    style J fill:#ffcc99
```

## Error Handling & Resilience

```mermaid
graph TD
    A[Input Validation] --> B{Valid?}
    B -->|❌ Invalid| C[Display Error & Exit]
    B -->|✅ Valid| D[Environment Check]
    
    D --> E{API Keys Present?}
    E -->|❌ Missing| F[Display Setup Instructions]
    E -->|✅ Present| G[Configuration Validation]
    
    G --> H{Config Valid?}
    H -->|❌ Invalid| I[Display Config Errors]
    H -->|✅ Valid| J[Start Processing]
    
    J --> K[Node Processing]
    K --> L{Node Success?}
    L -->|❌ Failed| M[Log Error & Continue]
    L -->|✅ Success| N[Next Node]
    
    M --> O[Update Error Metrics]
    N --> P{More Nodes?}
    P -->|Yes| K
    P -->|No| Q[Generate Summary]
    
    O --> P
    Q --> R[Display Results & Errors]
    
    subgraph "Resilience Features"
        S1[Graceful Degradation]
        S2[Comprehensive Logging]
        S3[Cost Tracking on Failures]
        S4[Checkpoint Support]
        S5[Retry Logic]
    end
```

## Usage Examples

### Basic Usage
```bash
# Simple extraction with Claude
python extractor_langgraph.py messages.jsonl triples.jsonl --provider claude

# With custom batch size and specific types
python extractor_langgraph.py messages.jsonl triples.jsonl \
  --provider openai \
  --batch-size 15 \
  --extract-types question answer
```

### Advanced Usage
```bash
# Full monitoring and analysis
ENABLE_LLM_RECORDING=true python extractor_langgraph.py \
  messages.jsonl triples.jsonl \
  --provider claude \
  --extract-types strategy analysis \
  --log-level DEBUG

# Fast processing for large datasets
python extractor_langgraph.py messages.jsonl triples.jsonl \
  --provider claude \
  --skip-qa-linking \
  --batch-size 50
```

### Analysis & Testing
```bash
# Token estimation before processing
python extractor_langgraph.py messages.jsonl triples.jsonl \
  --provider claude \
  --estimate-tokens

# Dry run validation
python extractor_langgraph.py messages.jsonl triples.jsonl \
  --provider claude \
  --dry-run
```

## Performance Characteristics

| Metric | Before Optimization | After Optimization | Improvement |
|--------|-------------------|-------------------|-------------|
| **Q&A Linking Tokens** | ~500k per batch | ~5k per batch | **99% reduction** |
| **Batch Size** | Fixed 5 questions | Dynamic 3-8 questions | **Adaptive** |
| **Answer Candidates** | 1,939 all answers | 20 filtered answers | **97% reduction** |
| **Processing Speed** | Hours | Minutes | **10x faster** |
| **API Cost** | Very High | Moderate | **90% reduction** |
| **Rate Limit Errors** | Common | Rare | **Automatic prevention** |

## System Requirements

- **Python 3.8+**
- **Required APIs**: OpenAI API key OR Anthropic API key
- **Dependencies**: LangGraph, OpenAI/Anthropic client libraries
- **Memory**: ~100MB for processing, ~500MB for large datasets
- **Storage**: SQLite database for recording (optional)

## Monitoring & Observability

The system provides comprehensive monitoring through:

1. **Real-time Logging**: Progress bars, batch information, error tracking
2. **Cost Tracking**: Per-call, per-message-type, and total cost analysis  
3. **Performance Metrics**: Processing time, success rates, token efficiency
4. **Interactive Dashboard**: Streamlit app for detailed analysis
5. **Export Capabilities**: JSON summaries, CSV exports, detailed reports

This architecture balances **simplicity** (easy CLI usage), **efficiency** (smart batching and filtering), and **observability** (comprehensive monitoring) for production use.