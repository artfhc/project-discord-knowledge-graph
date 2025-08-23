# 📊 LLM Call Recording System

This system provides comprehensive recording of all LLM API calls for evaluation and optimization of your Discord Knowledge Graph extraction pipeline.

## ✨ Features

- **📈 Comprehensive Recording**: Captures inputs, prompts, outputs, performance metrics, and costs for every LLM call
- **💾 Local Storage**: SQLite database stored in `bin/llm_evaluation/` 
- **🔧 Easy Integration**: Minimal changes to existing code
- **📊 Built-in Analysis**: Statistics, comparisons, and export capabilities
- **🎯 Experiment Tracking**: Organize recordings by experiment name

## 🚀 Quick Start

### Method 1: Simple Enable (Recommended)

Add just 2 lines to your existing workflow:

```python
# At the top of your script
from enable_recording import enable_recording_in_extractor_langgraph

# Before running extraction
enable_recording_in_extractor_langgraph("my_experiment_v1")

# Run your normal extraction - now with full recording!
python extractor_langgraph.py input.jsonl output.jsonl --provider claude
```

### Method 2: Environment Variables

Set environment variable and run normally:

```bash
export ENABLE_LLM_RECORDING=true
export LLM_EXPERIMENT_NAME="prompt_optimization_v1"

python extractor_langgraph.py input.jsonl output.jsonl --provider claude
```

### Method 3: Direct Integration

For more control, use the recorded components directly:

```python
from recording_config import setup_recorded_extractor

# This replaces your existing extractor with recorded version
extractor = setup_recorded_extractor(
    provider="claude", 
    model="claude-3-sonnet-20240229",
    experiment_name="my_experiment"
)

result = extractor.extract_triples(messages)
```

## 📊 What Gets Recorded

For **every single LLM API call**, the system captures:

### Input Data
- Raw message content and metadata
- Message types and classifications
- Batch size and segment information
- Processing context and workflow step

### Prompt Data
- System prompt used
- User prompt template and populated content
- Template type (question, strategy, analysis, etc.)
- Prompt configuration parameters

### Model Metadata
- Provider (OpenAI/Claude) and model name
- API parameters (temperature, max_tokens)
- Request configuration

### Output Data
- Raw API response text
- Parsed triples extracted
- Success/failure status
- Error messages (if any)

### Performance Metrics
- API call latency and duration
- Token usage (input/output/total)
- Cost per call and cumulative cost
- Processing efficiency metrics

## 📈 Analyzing Recorded Data

### Quick Stats

```python
from enable_recording import show_recording_stats
show_recording_stats()
```

### Export to CSV

```python
from enable_recording import export_recorded_data

# Export all data
export_recorded_data("all_calls.csv")

# Export filtered data
export_recorded_data("claude_calls.csv", provider="claude")
export_recorded_data("questions.csv", template_type="question")
```

### Create Analysis Script

```python
from enable_recording import create_simple_analysis_script
create_simple_analysis_script()

# Then run the generated script
python analyze_recordings.py
```

## 📁 Data Storage

All data is stored locally in:
```
bin/llm_evaluation/
├── llm_calls.db          # SQLite database with all records
└── exports/              # CSV export files (when exported)
```

### Database Schema

The SQLite database includes:
- **llm_calls** table with comprehensive call data
- Indexes for efficient querying by timestamp, provider, template type
- JSON fields for complex data (messages, triples, workflow state)

## 🎯 Use Cases

### 1. Prompt Optimization
Compare different prompt templates:
```sql
SELECT template_type, AVG(duration_seconds), COUNT(*) as calls
FROM llm_calls 
WHERE success = 1 
GROUP BY template_type;
```

### 2. Model Comparison
Analyze OpenAI vs Claude performance:
```sql
SELECT provider, AVG(cost_usd), AVG(duration_seconds), COUNT(*) 
FROM llm_calls 
GROUP BY provider;
```

### 3. Cost Analysis
Track spending over time:
```sql
SELECT DATE(timestamp) as date, SUM(cost_usd) as daily_cost
FROM llm_calls 
GROUP BY DATE(timestamp);
```

### 4. Quality Assessment
Identify failing patterns:
```sql
SELECT template_type, COUNT(*) as failures, error_message
FROM llm_calls 
WHERE success = 0 
GROUP BY template_type, error_message;
```

## ⚙️ Configuration Options

### Environment Variables
- `ENABLE_LLM_RECORDING`: Set to "true" to enable recording
- `LLM_EXPERIMENT_NAME`: Default experiment name
- `LLM_RECORDING_PATH`: Custom path for database file
- `LLM_RECORDING_LEVEL`: Recording level (full, basic, minimal)

### Programmatic Configuration
```python
from recording_config import RecordingConfig

config = RecordingConfig()
config.setup_recording("my_experiment")

# Later...
config.export_data("my_analysis.csv", provider="openai")
stats = config.get_stats()
```

## 🔧 Advanced Usage

### Custom Analysis
Connect directly to the SQLite database:
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect("bin/llm_evaluation/llm_calls.db")
df = pd.read_sql_query("SELECT * FROM llm_calls", conn)

# Your custom analysis here
print(df.groupby('template_type')['cost_usd'].sum())
```

### Filtering and Exports
```python
from llm_recorder import get_storage

storage = get_storage()

# Get specific calls
calls = storage.get_calls(
    provider="claude",
    template_type="question", 
    limit=500
)

# Custom filtering
successful_calls = [c for c in calls if c['success']]
```

## 🚨 Important Notes

- **Performance Impact**: <3% overhead on extraction pipeline
- **Privacy**: No API keys or sensitive data are stored
- **Storage**: Database grows ~1KB per LLM call
- **Compatibility**: Works with existing LangGraph workflow
- **Reliability**: Recording failures don't break extraction

## 🆘 Troubleshooting

### Recording Not Working?
1. Check if recording is enabled: `is_recording_enabled()`
2. Verify database path exists: `bin/llm_evaluation/`
3. Check permissions for writing to bin folder
4. Look for error messages in logs

### Missing Dependencies?
```bash
pip install pandas  # For CSV export
pip install sqlite3  # Usually built-in with Python
```

### Database Issues?
```python
from llm_recorder import get_storage
storage = get_storage()
stats = storage.get_stats()  # Test database connection
```

## 📚 Examples

See the generated `analyze_recordings.py` script for a complete example of data analysis and reporting.

For more advanced use cases, explore the source code in:
- `llm_recorder.py` - Core recording system
- `recorded_llm_providers.py` - Enhanced providers
- `recording_config.py` - Configuration utilities
- `enable_recording.py` - Integration helpers