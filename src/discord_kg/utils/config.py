"""Configuration management using Pydantic"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""
    
    # Discord
    discord_bot_token: str
    discord_server_id: int
    
    # OpenAI
    openai_api_key: str
    
    # Neo4j
    neo4j_uri: str
    neo4j_username: str = "neo4j"
    neo4j_password: str
    
    # PostgreSQL
    database_url: str
    
    # Backblaze B2
    b2_application_key_id: str
    b2_application_key: str
    b2_bucket_name: str
    
    # Application
    log_level: str = "INFO"
    batch_size: int = 100
    max_workers: int = 4
    
    # Web
    streamlit_server_port: int = 8501
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    class Config:
        env_file = ".env"

# Global settings instance
settings = Settings()