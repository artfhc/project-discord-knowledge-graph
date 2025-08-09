#!/usr/bin/env python3
"""Start web services (API + Streamlit)"""

import subprocess
import sys
import click
from src.discord_kg.utils.config import settings

@click.command()
@click.option('--api-only', is_flag=True, help='Start API server only')
@click.option('--streamlit-only', is_flag=True, help='Start Streamlit only')
def main(api_only: bool, streamlit_only: bool):
    """Start web services"""
    
    if not api_only:
        # Start Streamlit
        click.echo("Starting Streamlit app...")
        subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", 
            "src/discord_kg/web/streamlit_app.py",
            "--server.port", str(settings.streamlit_server_port)
        ])
    
    if not streamlit_only:
        # Start FastAPI
        click.echo("Starting FastAPI server...")
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "src.discord_kg.web.api:app",
            "--host", settings.api_host,
            "--port", str(settings.api_port),
            "--reload"
        ])

if __name__ == "__main__":
    main()