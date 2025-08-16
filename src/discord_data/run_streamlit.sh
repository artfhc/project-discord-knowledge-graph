#!/bin/bash
echo "Starting Discord Embeds Analysis Dashboard..."
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Launching Streamlit app..."
streamlit run streamlit_app.py