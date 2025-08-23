# 📊 LLM Evaluation Dashboard

A comprehensive Streamlit application for analyzing and evaluating LLM API calls recorded during Discord Knowledge Graph extraction.

## 🚀 Quick Start

### Option 1: Using the Launch Script
```bash
cd src/discord_data/llm_evaluation_dashboard/
./run_dashboard.sh
```

### Option 2: Manual Launch
```bash
cd src/discord_data/llm_evaluation_dashboard/
pip install -r requirements.txt
streamlit run llm_evaluation_app.py
```

The dashboard will be available at: **http://localhost:8501**

## 📊 Dashboard Features

### 📈 Overview Metrics
- Total API calls made
- Success rate across all calls
- Total cost and token usage
- Average call duration

### 🔍 Six Analysis Tabs

#### 1. **📊 Call Analytics**
- Success rates by template type
- Token usage distribution 
- Duration vs token count scatter plots
- Performance correlations

#### 2. **🎯 Template Performance**
- Comprehensive performance metrics per template
- Cost analysis by template type
- Average triples extracted per template
- Success rate comparisons

#### 3. **⚖️ Provider Comparison**
- OpenAI vs Claude performance analysis
- Cost distribution between providers
- Speed vs cost efficiency analysis
- Provider-specific statistics

#### 4. **💰 Cost Analysis**
- Daily cost trends over time
- Cost distribution analysis
- Cost per triple efficiency metrics
- Budget tracking and optimization insights

#### 5. **🕒 Time Analysis**
- Hourly activity patterns
- API call timeline visualization
- Duration analysis by template type
- Peak usage identification

#### 6. **🔍 Call Details**
- Searchable call records
- Individual call examination
- Prompt and response analysis
- Error investigation and debugging

## 🎛️ Interactive Features

### **Filters & Controls**
- **Date Range**: Filter calls by specific date ranges
- **Experiment Filter**: Focus on specific experiment runs
- **Provider Filter**: Analyze OpenAI or Claude separately
- **Template Type Filter**: Examine specific message types
- **Success Status**: View only successful or failed calls

### **Search & Exploration**
- Full-text search across prompts and responses
- Drill-down into individual API calls
- Export capabilities for further analysis
- Real-time filtering and updates

## 📁 Data Source

The dashboard automatically connects to your recorded LLM call data:

**Default Path**: `../../discord_kg/extraction/llm_powered/bin/llm_evaluation/llm_calls.db`

You can also specify a custom database path in the sidebar.

## 🔧 Prerequisites

### Required Data
The dashboard requires recorded LLM call data. Generate data by running extractions with recording enabled:

```bash
export ENABLE_LLM_RECORDING=true
export LLM_EXPERIMENT_NAME="my_analysis_experiment"
python extractor_langgraph.py input.jsonl output.jsonl --provider claude
```

### Dependencies
- Python 3.7+
- Streamlit
- Pandas
- Plotly
- NumPy
- SQLite (built-in with Python)

## 📊 Use Cases

### **Prompt Optimization**
- Compare success rates across different prompt templates
- Identify which prompts generate the most triples
- Analyze cost-effectiveness of different prompt strategies

### **Model Selection**
- Compare OpenAI vs Claude performance metrics
- Analyze cost vs quality trade-offs
- Determine optimal model for specific use cases

### **Cost Management**
- Track daily/hourly spending patterns
- Identify expensive operations and optimize
- Calculate ROI of different extraction strategies

### **Performance Tuning**
- Find optimal batch sizes for efficiency
- Identify slow operations and bottlenecks
- Monitor system performance over time

### **Quality Assessment**
- Examine failed API calls and error patterns
- Validate extraction quality across experiments
- Debug prompt and response issues

## 📈 Dashboard Screenshots

The dashboard provides:
- **Interactive Charts**: Plotly-powered visualizations
- **Real-time Filtering**: Dynamic data exploration
- **Detailed Analysis**: Drill-down capabilities
- **Export Options**: Data download for external analysis

## 🛠️ Customization

### Adding New Metrics
Edit `llm_evaluation_app.py` to add custom analysis:

```python
# Example: Add new metric
custom_metric = df.groupby('template_type')['your_field'].mean()
st.dataframe(custom_metric)
```

### Custom Visualizations
Add new charts using Plotly:

```python
fig = px.scatter(df, x='field1', y='field2', color='provider')
st.plotly_chart(fig, use_container_width=True)
```

## 🔍 Troubleshooting

### "Database file not found"
- Ensure you've run extractions with `ENABLE_LLM_RECORDING=true`
- Check the database path in the sidebar
- Verify the relative path is correct

### "No data found"
- Run some LLM extractions with recording enabled
- Check that the database contains records
- Verify date range filters aren't too restrictive

### Performance Issues
- Large datasets may load slowly - use date range filters
- Consider sampling for very large datasets
- Close unused browser tabs to free memory

## 🚀 Advanced Usage

### Automated Reports
Run the dashboard in headless mode for automated reporting:

```python
# Create custom analysis scripts using the same data loading functions
from llm_evaluation_app import load_data
df = load_data("path/to/database.db")
# Generate custom reports...
```

### Integration with Other Tools
- Export data to CSV for external analysis
- Connect to Jupyter notebooks for advanced analytics
- Import data into BI tools like Tableau or PowerBI

## 📞 Support

For issues or feature requests, check the main project documentation or create an issue in the repository.