# 🔍 Knowledge Graph Extraction Evaluator

**Interactive Streamlit app for comparing LLM vs Rule-based extraction outputs side-by-side.**

## 🎯 Purpose

This evaluation app helps you:
- **Compare extraction quality** between different methods
- **Analyze individual messages** and their extracted triples
- **Identify strengths and weaknesses** of each approach
- **Make data-driven decisions** about which method to use
- **Debug extraction issues** with detailed breakdowns

## 🚀 Quick Start

### Step 1: Launch the App
```bash
cd src/discord_data/extraction

# Option A: Using launch script
./run_app.sh

# Option B: Manual launch
pip install -r requirements.txt
streamlit run app.py
```

### Step 2: Import Your Data
1. **The app will open** in your browser at `http://localhost:8501`
2. **Import files** using either:
   - **📤 File Upload**: Drag & drop JSONL files directly
   - **📂 Local Paths**: Enter file paths on your system
3. **Start comparing** once data is loaded!

## 📊 Features

### 1. **📈 Overview Dashboard**
- Total extraction counts comparison
- Extraction rate metrics
- Predicate distribution charts
- High-level performance comparison

### 2. **🔍 Message-Level Comparison**
- **Side-by-side triple comparison** for individual messages
- **Filter messages** by extraction type, message type, or author
- **Original message context** with metadata
- **Confidence scoring** visualization
- **Interactive message browser**

### 3. **📊 Analytics Deep Dive**
- **Confidence distribution analysis**
- **Temporal extraction patterns**
- **Statistical summaries** (mean, median, std dev)
- **Method performance over time**

### 4. **🎯 Quality Analysis**
- **Agreement metrics** between methods
- **Top disagreement identification**
- **Coverage analysis** (which method extracts more)
- **Overlap scoring** for predicate types

## 📁 Data Requirements

The app requires you to import extraction result files:

### Import Methods
1. **📤 File Upload**: Drag & drop files directly into the web interface
2. **📂 Local Paths**: Enter file paths on your system

### Required Files
- **Rule-based results** (required): JSONL file with extraction triples
- **LLM results** (optional): JSONL file with LLM extraction triples  
- **Preprocessed messages** (optional): JSONL file with classified Discord messages (Step 2 output)

### Common File Locations
```
Rule-based: src/discord_kg/extraction/rule_based/step3_test_results.jsonl
LLM:        src/discord_data/extraction/extraction_llm_summary.jsonl
Preprocessed: src/discord_kg/preprocessing/sample_results.jsonl
```

### Data Format Expected

**Extraction files** (JSONL format):
```json
{
  "subject": "user123",
  "predicate": "asks_about", 
  "object": "DCA strategy",
  "message_id": "1019601508913926295",
  "segment_id": "segment-794992db",
  "timestamp": "2022-09-14T13:32:23.005000+00:00",
  "confidence": 0.85
}
```

**Preprocessed message files** (JSONL format):
```json
{
  "message_id": "1019601508913926295",
  "segment_id": "segment-794992db", 
  "author": "user123",
  "timestamp": "2022-09-14T13:32:23.005000+00:00",
  "type": "question",
  "confidence": 0.85,
  "clean_text": "What's the best DCA strategy for TQQQ?",
  "channel": "general",
  "mentions": []
}
```

## 🎛️ App Interface

### Navigation
The app has 4 main views accessible via the sidebar:

#### 📈 Overview
- **Metrics cards** showing total counts and rates
- **Bar charts** comparing extraction volumes
- **Predicate distribution** analysis

#### 🔍 Message Comparison  
- **Message selector** with filtering options
- **Original message display** with full metadata
- **Side-by-side triple comparison** with confidence colors
- **Comparison metrics** (overlap, counts)

#### 📊 Analytics
- **Confidence histograms** for each method
- **Statistical breakdowns** and summaries
- **Temporal analysis** showing extraction patterns over time

#### 🎯 Quality Analysis
- **Agreement metrics** between methods
- **Disagreement analysis** highlighting problem cases
- **Coverage comparison** (which method finds more)

### Filtering Options

**Message Comparison View:**
- **All Messages** - Show all available messages
- **Has Rule-based Only** - Messages only extracted by rule-based
- **Has LLM Only** - Messages only extracted by LLM
- **Has Both** - Messages extracted by both methods
- **Message Type** - Filter by question/answer/alert/strategy

### Visual Elements

**Confidence Color Coding:**
- 🟢 **Green** - High confidence (≥0.8)
- 🟡 **Yellow** - Medium confidence (0.6-0.8)
- 🔴 **Red** - Low confidence (<0.6)

**Method Color Coding:**
- 🟢 **Green** - Rule-based extractions
- 🟣 **Purple** - LLM-based extractions

## 📋 Use Cases

### 1. **Quality Assessment**
Compare extraction quality on the same messages:
```
1. Go to "Message Comparison"
2. Filter: "Has Both" 
3. Browse messages to see side-by-side results
4. Look for patterns in disagreements
```

### 2. **Method Coverage Analysis**
See which method covers more messages:
```
1. Go to "Overview" 
2. Check extraction rate metrics
3. Go to "Quality Analysis"
4. Review coverage statistics
```

### 3. **Debugging Extraction Issues**
Find problematic extractions:
```
1. Go to "Quality Analysis"
2. Check "Top Disagreements" 
3. Click on high-disagreement messages
4. Analyze why methods differ
```

### 4. **Confidence Analysis**
Understand extraction confidence:
```
1. Go to "Analytics"
2. Review confidence distributions
3. Identify low-confidence patterns
4. Compare method confidence profiles
```

## 🔧 Configuration

### Custom Data Paths
Edit `app.py` to point to different data locations:

```python
# Modify these paths in load_data() function
extraction_paths = [
    Path("your/custom/extraction/path"),
    # ... existing paths
]

preprocessing_paths = [
    Path("your/custom/preprocessing/path"), 
    # ... existing paths
]
```

### Port Configuration
Change the default port in `run_app.sh`:
```bash
streamlit run app.py --server.port 8502
```

## 🐛 Troubleshooting

### Data Not Loading
**Problem:** Files not importing correctly

**Solutions:**
1. Check JSONL file format is correct
2. Ensure files contain valid JSON objects per line
3. Try uploading files instead of using paths
4. Check file permissions and paths
5. Use the "📋 Expected File Format" guide in the app

### Missing LLM Data
**Problem:** Only rule-based results available

**Solutions:**
1. Generate LLM extraction results first:
   ```bash
   cd src/discord_kg/extraction/llm_powered
   python extractor_llm.py ../../preprocessing/sample_results.jsonl llm_output.jsonl
   ```
2. Import the generated LLM file using the app's import interface
3. The app works fine with just rule-based data - LLM comparison is optional

### Performance Issues
**Problem:** App loading slowly

**Solutions:**
1. Reduce data size for testing
2. Use data sampling for large datasets
3. Check available system memory

### Import Errors
**Problem:** Missing dependencies

**Solutions:**
```bash
pip install -r eval_requirements.txt
```

## 🔄 Workflow Integration

### Typical Evaluation Workflow
1. **Generate extractions** using both methods
2. **Launch evaluation app**
3. **Import result files** via web interface
4. **Review overview** metrics
5. **Compare specific messages** of interest
6. **Analyze quality patterns**
7. **Make method selection** decision

### Continuous Evaluation
- Set up regular extraction runs
- Compare results across different datasets
- Track quality improvements over time
- Document findings for future reference

## 📈 Interpreting Results

### Good Signs
- ✅ **High overlap** in predicate types
- ✅ **Similar extraction rates** between methods
- ✅ **High confidence scores** across methods
- ✅ **Consistent results** on clear messages

### Warning Signs  
- ⚠️ **Large extraction count differences**
- ⚠️ **Low predicate overlap**
- ⚠️ **Many low-confidence extractions**
- ⚠️ **Inconsistent results** on similar messages

### Decision Criteria
- **Accuracy** - Which method produces more correct triples?
- **Coverage** - Which method extracts more relevant information?
- **Consistency** - Which method provides more reliable results?
- **Cost** - What are the trade-offs in time/money/resources?

## 🎯 Next Steps

After evaluation, consider:
1. **Hybrid approach** - Use best method per message type
2. **Ensemble methods** - Combine both approaches
3. **Fine-tuning** - Improve prompts or rules based on findings  
4. **Quality filtering** - Set confidence thresholds
5. **Iterative improvement** - Regular re-evaluation cycles

---

**Happy evaluating! 🚀**

For issues or questions, check the main project documentation or create an issue in the repository.