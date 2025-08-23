#!/bin/bash

# LLM Evaluation Dashboard Launcher
echo "🚀 Starting LLM Evaluation Dashboard..."

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found. Installing requirements..."
    pip install -r requirements.txt
fi

# Launch the dashboard
echo "📊 Launching dashboard at http://localhost:8501"
streamlit run llm_evaluation_app.py

echo "✅ Dashboard closed"