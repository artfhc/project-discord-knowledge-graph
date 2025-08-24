# Discord Knowledge Graph Extractor Architecture

This document provides visual diagrams and explanations of the `extractor_langgraph.py` system architecture.

## System Overview

```mermaid
graph TD
    A["CLI Entry Point extractor_langgraph.py"] --> B["Parse CLI Arguments"]
    B --> C{"Validation"}
    C -->|"Pass"| D["Optional Flags Processing"]
    C -->|"Fail"| E["Exit with Error"]
    
    D --> F["LLM Call Recording Setup"]
    F --> G["Create ExtractionWorkflow"]
    G --> H["Run Processing Pipeline"]
    H --> I["Generate Summary Report"]
    
    subgraph OptionalModes ["Optional Modes"]
        D1["estimate-tokens Token Analysis"]
        D2["dry-run Validation Only"]
        D3["skip-qa-linking Fast Mode"]
    end
    
    D --> D1
    D --> D2
    D --> D3
```

## CLI Options Flow

```mermaid
graph LR
    A["CLI Arguments"] --> B["Provider Selection"]
    A --> C["Batch Configuration"]
    A --> D["Message Type Filtering"]
    A --> E["Processing Options"]
    
    B --> B1["provider openai/claude"]
    B --> B2["model specific-model"]
    
    C --> C1["batch-size 20 Maximum batch size"]
    C --> C2["Dynamic Token Adjustment"]
    
    D --> D1["extract-types question answer strategy"]
    D --> D2["Process All Types Default"]
    
    E --> E1["skip-qa-linking Faster processing"]
    E --> E2["enable-checkpoints Resume capability"]
    E --> E3["log-level DEBUG Detailed logging"]
```

## LangGraph Node Architecture

This diagram shows the individual nodes in the LangGraph workflow and how they connect:

```mermaid
graph TD
    START(["START"]) --> PP["preprocessing_node"]
    PP --> CL["classification_node"]
    CL --> RT["routing_node"]
    
    RT --> EQ["extract_question_node"]
    RT --> ES["extract_strategy_node"]
    RT --> EA["extract_analysis_node"]
    RT --> EAn["extract_answer_node"]
    RT --> EAl["extract_alert_node"]
    RT --> EP["extract_performance_node"]
    RT --> ED["extract_discussion_node"]
    
    EQ --> RT2["routing_node (check next)"]
    ES --> RT2
    EA --> RT2
    EAn --> RT2
    EAl --> RT2
    EP --> RT2
    ED --> RT2
    
    RT2 --> QA["qa_linking_node"]
    RT2 --> AG["aggregation_node"]
    
    QA --> AG
    AG --> CT["cost_tracking_node"]
    CT --> END(["END"])
    
    subgraph NodeDetails ["Node Functions"]
        PP_D["preprocessing_node: Clean & validate messages, group by segments"]
        CL_D["classification_node: Classify messages into types using rules"]
        RT_D["routing_node: Route to next extraction step based on available types"]
        EQ_D["extract_question_node: Extract triples from question messages"]
        ES_D["extract_strategy_node: Extract triples from strategy messages"]
        EA_D["extract_analysis_node: Extract triples from analysis messages"]
        EAn_D["extract_answer_node: Extract triples from answer messages"]
        EAl_D["extract_alert_node: Extract triples from alert messages"]
        EP_D["extract_performance_node: Extract triples from performance messages"]
        ED_D["extract_discussion_node: Extract triples from discussion messages"]
        QA_D["qa_linking_node: Link questions to answers using LLM"]
        AG_D["aggregation_node: Aggregate and validate all extracted triples"]
        CT_D["cost_tracking_node: Generate final cost summary and analytics"]
    end
    
    style START fill:#90EE90
    style END fill:#FFB6C1
    style PP fill:#87CEEB
    style CL fill:#DDA0DD
    style RT fill:#F0E68C
    style RT2 fill:#F0E68C
    style QA fill:#FFA07A
    style AG fill:#98FB98
    style CT fill:#F4A460
```

## Routing Logic in Detail

The `routing_node` contains sophisticated conditional logic:

```mermaid
graph TD
    RT["routing_node called"] --> A1{"extract_types filter active?"}
    
    A1 -->|"Yes"| A2["Check only allowed message types"]
    A1 -->|"No"| A3["Check all message types: question, strategy, analysis, answer, alert, performance, discussion"]
    
    A2 --> B["For each allowed type, check if messages exist"]
    A3 --> B
    
    B --> C["Get list of processed extraction results"]
    C --> D{"Find first unprocessed type with messages"}
    
    D -->|"Found"| E["Route to extract_TYPE_node"]
    D -->|"None found"| F{"Should skip Q&A linking?"}
    
    F -->|"Yes"| G["Route to aggregation_node"]
    F -->|"No"| H{"Has questions AND answers?"}
    
    H -->|"Yes"| I{"Q&A linking already done?"}
    H -->|"No"| G
    
    I -->|"Yes"| G
    I -->|"No"| J["Route to qa_linking_node"]
    
    E --> K["Node processes messages and returns to routing_node"]
    K --> D
    
    J --> L["Q&A linking completes"]
    L --> G
    G --> M["aggregation_node"]
    M --> N["cost_tracking_node"]
    N --> END_NODE(["END"])
    
    style RT fill:#F0E68C
    style F fill:#FFE4B5
    style H fill:#FFE4B5
    style I fill:#FFE4B5
    style END_NODE fill:#FFB6C1
```

## Node State Flow

Each node receives and updates the WorkflowState:

```mermaid
graph LR
    subgraph StateIn ["Input State"]
        SI1["raw_messages: List[Dict]"]
        SI2["llm_provider: str"]
        SI3["batch_size: int"]
        SI4["extract_types: List[str]"]
        SI5["should_skip_qa_linking: bool"]
    end
    
    subgraph NodeProcess ["Node Processing"]
        NP1["Read from state"]
        NP2["Process messages"]
        NP3["Create NodeResult"]
        NP4["Update state"]
    end
    
    subgraph StateOut ["Output State"]
        SO1["processed_messages: List[Dict]"]
        SO2["classified_messages: Dict"]
        SO3["extracted_triples: List[Triple]"]
        SO4["qa_links: List[Triple]"]
        SO5["aggregated_results: List[Triple]"]
        SO6["cost_summary: Dict"]
    end
    
    StateIn --> NodeProcess
    NodeProcess --> StateOut
    
    style NodeProcess fill:#87CEEB
```

## Data Processing Pipeline (Simplified View)

```mermaid
graph TD
    A["Input JSONL File Discord Messages"] --> B["Preprocessing Node"]
    B --> C["Classification Node"]
    C --> D["Message Type Routing"]
    
    D --> E1["Question Extraction"]
    D --> E2["Strategy Extraction"]  
    D --> E3["Analysis Extraction"]
    D --> E4["Answer Extraction"]
    D --> E5["Alert Extraction"]
    D --> E6["Performance Extraction"]
    D --> E7["Discussion Extraction"]
    
    E1 --> F{"Q&A Linking Enabled?"}
    E2 --> G["Aggregation Node"]
    E3 --> G
    E4 --> F
    E5 --> G
    E6 --> G
    E7 --> G
    
    F -->|"Yes"| H["Q&A Linking Node"]
    F -->|"No"| G
    H --> G
    
    G --> I["Cost Tracking Node"]
    I --> J["Output JSONL File Extracted Triples"]
    
    style A fill:#e1f5fe
    style J fill:#e8f5e8
    style F fill:#fff3e0
    style H fill:#fce4ec
```

## Dynamic Batch Sizing Logic

```mermaid
graph TD
    A["Messages to Process"] --> B["Estimate Tokens per Message"]
    B --> C["Calculate Optimal Batch Size"]
    C --> D{"Compare with User Batch Size"}
    
    D -->|"Optimal < User"| E["Use Optimal Size Token-limited"]
    D -->|"Optimal >= User"| F["Use User Size User preference respected"]
    
    E --> G["Log Adjustment"]
    F --> H["Process Batch"]
    G --> H
    
    H --> I["API Call with Batch"]
    I --> J{"More Messages?"}
    J -->|"Yes"| A
    J -->|"No"| K["Complete"]
    
    subgraph TokenLimits ["Token Limits by Provider"]
        L1["Claude: ~13,333 tokens/batch 50k tokens/min ÷ 3"]
        L2["OpenAI: ~30,000 tokens/batch 90k tokens/min ÷ 3"]
    end
```

## Q&A Linking Process Simplified

```mermaid
graph TD
    A["131 Questions 1,939 Answers"] --> B["Batch Questions 3-6 per batch"]
    
    B --> C["For Each Question Batch"]
    C --> D["Filter Answers: 1. Direct Replies 2. Next 20 Chronological"]
    
    D --> E["Question Batch + 20 Filtered Answers"]
    E --> F["LLM API Call Which answers match which questions?"]
    
    F --> G["Extract Q&A Links question_id → answered_by → answer_id"]
    G --> H{"More Question Batches?"}
    
    H -->|"Yes"| C
    H -->|"No"| I["Combine All Q&A Links"]
    
    subgraph EfficiencyImprovement ["Efficiency Improvement"]
        J["Before: 5 questions × 1,939 answers = 500k tokens per batch"]
        K["After: 6 questions × 20 answers = 5k tokens per batch"]
        J --> K
    end
```

## LLM Recording and Monitoring

```mermaid
graph TD
    A["Enable Recording ENABLE_LLM_RECORDING=true"] --> B["Monkey Patch LLM Providers"]
    
    B --> C["Intercept All API Calls"]
    C --> D["Record Call Metadata: Timestamp, Provider/Model, Tokens & Cost, Success/Failure, Processing Time, Batch Size"]
    
    D --> E["Store in SQLite Database llm_calls.db"]
    E --> F["Analysis Dashboard llm_evaluation_app.py"]
    
    F --> G["Interactive Visualizations: Cost Analysis, Success Rates, Token Usage, Batch Efficiency, Template Performance"]
    
    subgraph DashboardFeatures ["Dashboard Features"]
        H1["Cost Trends"]
        H2["Performance Metrics"]
        H3["Success Rates by Template"]
        H4["Batch Size Analysis"]
        H5["Individual Call Details"]
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
    A["extractor_langgraph.py CLI Entry Point"] --> B["workflow.py LangGraph Orchestration"]
    
    B --> C["nodes.py Processing Nodes"]
    B --> D["workflow_state.py State Management"]
    
    C --> E["llm_providers.py OpenAI/Claude APIs"]
    C --> F["token_utils.py Dynamic Batching"]
    C --> G["config.py Prompt Templates"]
    
    A --> H["enable_recording.py LLM Call Monitoring"]
    H --> I["llm_recorder.py Database Storage"]
    I --> J["llm_evaluation_app.py Analysis Dashboard"]
    
    style A fill:#ff9999
    style B fill:#99ccff
    style E fill:#99ff99
    style J fill:#ffcc99
```

## Error Handling and Resilience

```mermaid
graph TD
    A["Input Validation"] --> B{"Valid?"}
    B -->|"Invalid"| C["Display Error & Exit"]
    B -->|"Valid"| D["Environment Check"]
    
    D --> E{"API Keys Present?"}
    E -->|"Missing"| F["Display Setup Instructions"]
    E -->|"Present"| G["Configuration Validation"]
    
    G --> H{"Config Valid?"}
    H -->|"Invalid"| I["Display Config Errors"]
    H -->|"Valid"| J["Start Processing"]
    
    J --> K["Node Processing"]
    K --> L{"Node Success?"}
    L -->|"Failed"| M["Log Error & Continue"]
    L -->|"Success"| N["Next Node"]
    
    M --> O["Update Error Metrics"]
    N --> P{"More Nodes?"}
    P -->|"Yes"| K
    P -->|"No"| Q["Generate Summary"]
    
    O --> P
    Q --> R["Display Results & Errors"]
    
    subgraph ResilienceFeatures ["Resilience Features"]
        S1["Graceful Degradation"]
        S2["Comprehensive Logging"]
        S3["Cost Tracking on Failures"]
        S4["Checkpoint Support"]
        S5["Retry Logic"]
    end
```

## Token-Aware Batching Flow

```mermaid
flowchart TD
    A["Incoming Messages"] --> B["Estimate Message Tokens"]
    B --> C["Check Provider Rate Limits"]
    C --> D["Calculate Optimal Batch Size"]
    D --> E{"User Batch Size Limit?"}
    
    E -->|"Yes"| F["min(optimal, user_limit)"]
    E -->|"No"| G["Use Optimal Size"]
    
    F --> H["Create Batch"]
    G --> H
    H --> I["Send to LLM API"]
    I --> J["Process Response"]
    J --> K{"More Messages?"}
    
    K -->|"Yes"| A
    K -->|"No"| L["Complete"]
    
    subgraph RateLimits ["Rate Limits"]
        M1["Claude: 50k tokens/min"]
        M2["OpenAI: 90k tokens/min"]
        M3["Safety Margin: 80%"]
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

### Analysis and Testing
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

## Monitoring and Observability

The system provides comprehensive monitoring through:

1. **Real-time Logging**: Progress bars, batch information, error tracking
2. **Cost Tracking**: Per-call, per-message-type, and total cost analysis  
3. **Performance Metrics**: Processing time, success rates, token efficiency
4. **Interactive Dashboard**: Streamlit app for detailed analysis
5. **Export Capabilities**: JSON summaries, CSV exports, detailed reports

This architecture balances **simplicity** (easy CLI usage), **efficiency** (smart batching and filtering), and **observability** (comprehensive monitoring) for production use.