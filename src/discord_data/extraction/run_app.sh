#!/bin/bash
# Launch script for Knowledge Graph Extraction Evaluation App

echo "🔍 Discord Knowledge Graph - Extraction Evaluator"
echo "================================================="

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found. Installing dependencies..."
    pip install -r requirements.txt
fi

# Check for data files
echo "📊 Checking for extraction data..."

EXTRACTION_DIR="../../discord_data/extraction"
PREPROCESSING_DIR="../preprocessing"

if [ -f "$EXTRACTION_DIR/extraction_rule_based_summary.jsonl" ]; then
    echo "✅ Found rule-based extraction data"
else
    echo "⚠️  Rule-based extraction data not found at $EXTRACTION_DIR"
fi

if [ -f "$EXTRACTION_DIR/extraction_llm_summary.jsonl" ]; then
    echo "✅ Found LLM extraction data"
else
    echo "⚠️  LLM extraction data not found at $EXTRACTION_DIR"
    echo "   Generate LLM results first for full comparison"
fi

if [ -f "$PREPROCESSING_DIR/sample_results.jsonl" ]; then
    echo "✅ Found original messages"
else
    echo "⚠️  Original messages not found at $PREPROCESSING_DIR"
fi

echo ""
echo "🚀 Launching evaluation app..."
echo "   App will open in your default browser"
echo "   Press Ctrl+C to stop"
echo ""

# Launch streamlit app
streamlit run app.py --server.port 8501 --server.address localhost