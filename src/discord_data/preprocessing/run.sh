#!/bin/bash

# Discord Classification Evaluator Runner
# Installs dependencies and launches the Streamlit app

echo "🚀 Starting Discord Classification Evaluator..."

# Check if requirements are installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📦 Installing requirements..."
    pip install -r requirements.txt
fi

# Launch Streamlit app
echo "🌐 Launching Streamlit app..."
streamlit run app.py --server.port 8501 --server.headless false

echo "✅ App started! Open http://localhost:8501 in your browser"