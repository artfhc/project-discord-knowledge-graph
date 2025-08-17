# Discord Classification Evaluator

Interactive Streamlit app for analyzing and evaluating Discord message classification results.

## Features

- **Data Loading**: Upload JSONL files or specify file paths
- **Interactive Visualizations**:
  - Classification distribution pie chart
  - Confidence score histograms
  - Timeline analysis
  - Author activity analysis
- **Filtering & Search**:
  - Filter by classification type
  - Set confidence thresholds
  - Search message content
  - Author-based filtering
- **Export Capabilities**:
  - Download filtered data as CSV
  - Generate summary reports in JSON

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser to the displayed URL (typically `http://localhost:8501`)

3. Upload your JSONL classification results file or enter the file path

4. Explore the interactive visualizations and analysis tools

## Input Format

The app expects JSONL files with classified message data containing fields like:
- `message_id`: Unique message identifier
- `type`: Classification type (question, answer, alert, strategy)
- `confidence`: Classification confidence score (0-1)
- `content`: Original message content
- `author`: Message author
- `timestamp`: Message timestamp
- `channel`: Channel name

## Example Usage

```bash
# From the evaluation directory
streamlit run app.py

# Or with specific file
streamlit run app.py -- --file ../preprocessing/sample_results.jsonl
```