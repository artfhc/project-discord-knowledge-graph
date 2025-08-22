# Discord Knowledge Graph - LLM Extraction Flow Diagrams

## Current System Flow

```mermaid
graph TD
    A[Input: 4895 Messages] --> B[Group by Segment ID]
    B --> C[1248 Segments]
    
    C --> D[Process Segment 1]
    D --> E[Group by Message Type]
    
    E --> F[Questions: 1 msg]
    E --> G[Strategies: 124 msgs]
    E --> H[Analysis: 50 msgs]
    E --> I[Answers: 200 msgs]
    
    F --> F1[Adaptive Batch Processing]
    F1 --> F2[Batch #1: global indices 0:1]
    F2 --> F3{JSON Parse OK?}
    F3 -->|Yes| F4[Extract Triples]
    F3 -->|No| F5[Reduce Batch Size]
    F5 --> F2
    
    G --> G1[Adaptive Batch Processing]
    G1 --> G2[Batch #1: global indices 0:30]
    G2 --> G3{JSON Parse OK?}
    G3 -->|Yes| G4[Extract Triples]
    G3 -->|No| G5[Reduce to 15, retry 0:15]
    G5 --> G6[Retry Batch]
    G6 --> G4
    
    H --> H1[Similar Sequential Process...]
    I --> I1[Similar Sequential Process...]
    
    F4 --> J[Q&A Linking]
    G4 --> J
    H1 --> J
    I1 --> J
    
    J --> K[Combine All Triples]
    K --> L[Next Segment...]
    L --> M[Final Output: Triples]
    
    style F fill:#e1f5fe
    style G fill:#e8f5e8
    style H fill:#fff3e0
    style I fill:#fce4ec
    style J fill:#f3e5f5
```

## Current Issues Visualized

```mermaid
graph TD
    A[Segment Processing] --> B[Sequential Bottleneck]
    
    B --> C[Process Questions]
    C --> D[Wait for Questions to Complete]
    D --> E[Process Strategies]
    E --> F[Wait for Strategies to Complete]
    F --> G[Process Analysis]
    G --> H[Wait for Analysis to Complete]
    H --> I[Process Answers]
    I --> J[Q&A Linking]
    
    K[Error in Strategies] --> L[Retry Logic Scattered]
    L --> M[Manual State Tracking]
    M --> N[Complex Adaptive Batching]
    
    O[JSON Truncation Issues] --> P[Repetitive Error Handling]
    P --> Q[Hard to Debug Flow]
    
    style B fill:#ffcdd2
    style K fill:#ffcdd2
    style O fill:#ffcdd2
```

## LangGraph Enhanced System

```mermaid
graph TD
    A[Input: Messages] --> B[Segment Router Node]
    B --> C{Segment Complexity Analysis}
    
    C -->|Simple Messages| D[Fast Track Processing]
    C -->|Complex Messages| E[Careful Processing Branch]
    C -->|Mixed Complexity| F[Adaptive Processing Branch]
    
    E --> G[Parallel Extraction Hub]
    
    G --> H[Question Extractor Node]
    G --> I[Strategy Extractor Node] 
    G --> J[Analysis Extractor Node]
    G --> K[Answer Extractor Node]
    
    H --> H1{Extraction Success?}
    I --> I1{Extraction Success?}
    J --> J1{Extraction Success?}
    K --> K1{Extraction Success?}
    
    H1 -->|Failure| H2[Question Retry Node]
    I1 -->|Failure| I2[Strategy Retry Node]
    J1 -->|Failure| J2[Analysis Retry Node]
    K1 -->|Failure| K2[Answer Retry Node]
    
    H2 --> H3[Adaptive Batch Reduction]
    I2 --> I3[Adaptive Batch Reduction]
    J2 --> J3[Adaptive Batch Reduction]
    K2 --> K3[Adaptive Batch Reduction]
    
    H1 -->|Success| L[Aggregation Node]
    I1 -->|Success| L
    J1 -->|Success| L
    K1 -->|Success| L
    
    H3 --> L
    I3 --> L
    J3 --> L
    K3 --> L
    
    L --> M[Q&A Linking Node]
    M --> M1{Q&A Linking Success?}
    M1 -->|Failure| M2[Q&A Retry Node]
    M2 --> M3[Reduce Q&A Batch Size]
    M1 -->|Success| N[Validation Node]
    M3 --> N
    
    N --> O[Cost Tracking Node]
    O --> P[Output Generation Node]
    P --> Q[Final Triples Output]
    
    style H fill:#e1f5fe
    style I fill:#e8f5e8
    style J fill:#fff3e0
    style K fill:#fce4ec
    style G fill:#f3e5f5
    style L fill:#e8eaf6
```

## Parallel Processing Advantage

```mermaid
graph TD
    A[Current: Sequential Processing] --> A1[Total Time: T1 + T2 + T3 + T4]
    A1 --> A2[Questions: T1]
    A2 --> A3[Strategies: T2]
    A3 --> A4[Analysis: T3] 
    A4 --> A5[Answers: T4]
    
    B[LangGraph: Parallel Processing] --> B1[Total Time: MAX T1, T2, T3, T4]
    B1 --> B2[Questions: T1 ⚡]
    B1 --> B3[Strategies: T2 ⚡]
    B1 --> B4[Analysis: T3 ⚡]
    B1 --> B5[Answers: T4 ⚡]
    
    B2 --> C[Parallel Completion]
    B3 --> C
    B4 --> C
    B5 --> C
    
    C --> D[4x Potential Speedup]
    
    style A1 fill:#ffcdd2
    style B1 fill:#c8e6c9
    style D fill:#4caf50
```

## Smart Error Recovery Flow

```mermaid
graph TD
    A[Processing Node Encounters Error] --> B{Error Classification}
    
    B -->|JSON Truncation| C[Truncation Recovery]
    B -->|API Rate Limit| D[Rate Limit Recovery]
    B -->|Model Overload| E[Model Switch Recovery]
    B -->|Network Error| F[Network Recovery]
    
    C --> C1[Analyze Truncation Point]
    C1 --> C2[Reduce Batch Size by 50%]
    C2 --> C3[Retry with Smaller Batch]
    C3 --> G[Success Check]
    
    D --> D1[Exponential Backoff]
    D1 --> D2[Wait: 1s → 2s → 4s → 8s]
    D2 --> D3[Retry Original Request]
    D3 --> G
    
    E --> E1[Switch to Smaller Model]
    E1 --> E2[gpt-4 → gpt-3.5-turbo]
    E2 --> E3[Retry with Different Model]
    E3 --> G
    
    F --> F1[Network Retry Logic]
    F1 --> F2[Retry with Timeout Increase]
    F2 --> G
    
    G --> H{Recovery Successful?}
    H -->|Yes| I[Continue Processing]
    H -->|No| J[Escalate to Fallback Strategy]
    
    J --> K[Skip Problematic Batch]
    K --> L[Log for Manual Review]
    L --> I
    
    style C fill:#fff3e0
    style D fill:#e8f5e8
    style E fill:#e1f5fe
    style F fill:#fce4ec
```

## State Management Comparison

```mermaid
graph TD
    subgraph "Current Manual State Tracking"
        A1[LLMSegmentProcessor] --> A2[_global_type_offsets: Dict]
        A2 --> A3[Manual offset tracking]
        A3 --> A4[Error-prone state updates]
        A4 --> A5[Scattered state across methods]
    end
    
    subgraph "LangGraph Centralized State"
        B1[ExtractionState] --> B2[messages: List[Dict]]
        B1 --> B3[batch_sizes: Dict[str, int]]
        B1 --> B4[processed_counts: Dict[str, int]]
        B1 --> B5[error_counts: Dict[str, int]]
        B1 --> B6[cost_tracking: Dict[str, float]]
        B1 --> B7[extracted_triples: List[Triple]]
        B1 --> B8[retry_states: Dict[str, Any]]
    end
    
    C[Processing Nodes] --> B1
    D[Question Node] --> B1
    E[Strategy Node] --> B1
    F[Analysis Node] --> B1
    G[Answer Node] --> B1
    H[Q&A Linking Node] --> B1
    
    style A4 fill:#ffcdd2
    style B1 fill:#c8e6c9
```

## Implementation Migration Path

```mermaid
graph LR
    subgraph "Phase 1: Wrapper Approach"
        A1[Keep Existing Logic] --> A2[Wrap in LangGraph Nodes]
        A2 --> A3[Add Parallel Execution]
        A3 --> A4[Immediate 4x Speedup]
    end
    
    subgraph "Phase 2: Smart Routing"
        B1[Add Complexity Analysis] --> B2[Dynamic Model Selection]
        B2 --> B3[Cost-Aware Routing]
        B3 --> B4[Advanced Error Recovery]
    end
    
    subgraph "Phase 3: Full Rewrite"
        C1[LangGraph-Native Design] --> C2[State-First Architecture]
        C2 --> C3[Multi-Agent Coordination]
        C3 --> C4[Advanced Orchestration]
    end
    
    A4 --> B1
    B4 --> C1
    
    style A4 fill:#e8f5e8
    style B4 fill:#fff3e0
    style C4 fill:#e1f5fe
```

## Performance Metrics Visualization

```mermaid
graph TD
    A[Performance Comparison] --> B[Processing Time]
    A --> C[Error Recovery]
    A --> D[Observability]
    A --> E[Maintainability]
    
    B --> B1[Current: Sequential<br/>~4-5 minutes total]
    B --> B2[LangGraph: Parallel<br/>~1-2 minutes total]
    
    C --> C1[Current: Manual retry<br/>Complex scattered logic]
    C --> C2[LangGraph: Smart routing<br/>Centralized recovery]
    
    D --> D1[Current: Logs only<br/>Hard to debug]
    D --> D2[LangGraph: Visual graph<br/>Clear flow tracking]
    
    E --> E1[Current: Repetitive code<br/>Hard to extend]
    E --> E2[LangGraph: Modular nodes<br/>Easy to modify]
    
    style B1 fill:#ffcdd2
    style B2 fill:#c8e6c9
    style C1 fill:#ffcdd2
    style C2 fill:#c8e6c9
    style D1 fill:#ffcdd2
    style D2 fill:#c8e6c9
    style E1 fill:#ffcdd2
    style E2 fill:#c8e6c9
```

## Cost Optimization Flow

```mermaid
graph TD
    A[Message Batch] --> B{Complexity Analysis}
    
    B -->|Simple Questions| C[Use GPT-3.5-turbo<br/>Lower cost]
    B -->|Complex Analysis| D[Use GPT-4<br/>Higher accuracy]
    B -->|Strategy Discussion| E[Use Claude Haiku<br/>Fast processing]
    
    C --> F[Cost Tracking Node]
    D --> F
    E --> F
    
    F --> G{Cost Threshold Check}
    G -->|Under Budget| H[Continue Processing]
    G -->|Over Budget| I[Switch to Cheaper Models]
    
    I --> J[Reduce Quality Slightly]
    J --> K[Increase Batch Sizes]
    K --> H
    
    H --> L[Process with Optimal Model]
    
    style C fill:#c8e6c9
    style D fill:#fff3e0
    style E fill:#e1f5fe
    style I fill:#ffecb3
```

## Real-time Monitoring Dashboard Concept

```mermaid
graph TD
    A[LangGraph Dashboard] --> B[Processing Pipeline View]
    A --> C[Error Recovery Monitor]
    A --> D[Cost Tracking Panel]
    A --> E[Performance Metrics]
    
    B --> B1[Current Active Nodes]
    B --> B2[Batch Progress Bars]
    B --> B3[Queue Status]
    
    C --> C1[Failed Batches Count]
    C --> C2[Recovery Success Rate]
    C --> C3[Error Type Distribution]
    
    D --> D1[Cost per Message Type]
    D --> D2[Model Usage Statistics]
    D --> D3[Budget Utilization]
    
    E --> E1[Messages/Second Throughput]
    E --> E2[Average Response Time]
    E --> E3[Success Rate by Node]
    
    style A fill:#e8eaf6
    style B1 fill:#e1f5fe
    style C1 fill:#fff3e0
    style D1 fill:#e8f5e8
    style E1 fill:#fce4ec
```