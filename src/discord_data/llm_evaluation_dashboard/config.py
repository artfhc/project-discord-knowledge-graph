"""
Configuration settings for the LLM Evaluation Dashboard.
"""

import os
from pathlib import Path

# Dashboard configuration
DASHBOARD_CONFIG = {
    # Page settings
    "page_title": "LLM Evaluation Dashboard",
    "page_icon": "📊",
    "layout": "wide",
    
    # Default database path (relative to dashboard directory)
    "default_db_path": "../../discord_kg/extraction/llm_powered/bin/llm_evaluation/llm_calls.db",
    
    # Chart settings
    "default_chart_height": 400,
    "color_palette": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
    
    # Data processing
    "cache_ttl": 300,  # Cache TTL in seconds
    "max_records_display": 1000,  # Maximum records to show in detail view
    
    # Feature flags
    "show_debug_info": False,
    "enable_data_export": True,
    "show_raw_data": True,
}

# Metrics configuration
METRICS_CONFIG = {
    "overview_metrics": [
        {"name": "Total Calls", "field": "count", "format": "{:,}"},
        {"name": "Success Rate", "field": "success_rate", "format": "{:.1f}%"},
        {"name": "Total Cost", "field": "total_cost", "format": "${:.4f}"},
        {"name": "Avg Duration", "field": "avg_duration", "format": "{:.2f}s"},
        {"name": "Total Tokens", "field": "total_tokens", "format": "{:,}"},
    ],
    
    "cost_metrics": [
        "cost_per_token",
        "cost_per_triple", 
        "cost_per_call",
        "daily_cost",
        "hourly_cost"
    ],
    
    "performance_metrics": [
        "duration_seconds",
        "tokens_per_second",
        "success_rate",
        "error_rate"
    ]
}

# Chart configurations
CHART_CONFIG = {
    "success_rate_chart": {
        "type": "bar",
        "title": "Success Rate by Template Type",
        "x_axis": "template_type",
        "y_axis": "success_rate",
        "color_scheme": "viridis"
    },
    
    "cost_trend_chart": {
        "type": "line", 
        "title": "Daily Cost Trend",
        "x_axis": "date",
        "y_axis": "cost_usd",
        "color_scheme": "blues"
    },
    
    "token_distribution": {
        "type": "histogram",
        "title": "Token Usage Distribution",
        "x_axis": "total_tokens",
        "bins": 20
    }
}

# Database query configurations
QUERY_CONFIG = {
    "default_limit": 1000,
    "batch_size": 100,
    "timeout_seconds": 30,
    
    # Pre-defined queries for common analyses
    "common_queries": {
        "failed_calls": """
            SELECT * FROM llm_calls 
            WHERE success = 0 
            ORDER BY timestamp DESC
        """,
        
        "expensive_calls": """
            SELECT * FROM llm_calls 
            ORDER BY cost_usd DESC 
            LIMIT 100
        """,
        
        "recent_calls": """
            SELECT * FROM llm_calls 
            WHERE timestamp >= datetime('now', '-24 hours')
            ORDER BY timestamp DESC
        """,
        
        "template_performance": """
            SELECT 
                template_type,
                COUNT(*) as total_calls,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                AVG(duration_seconds) as avg_duration,
                AVG(cost_usd) as avg_cost,
                AVG(total_tokens) as avg_tokens
            FROM llm_calls 
            GROUP BY template_type
        """
    }
}

# Export configurations
EXPORT_CONFIG = {
    "csv_separator": ",",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "float_precision": 4,
    "max_export_records": 10000,
    
    "default_columns": [
        "timestamp", "experiment_name", "provider", "model_name",
        "template_type", "success", "duration_seconds", "total_tokens",
        "cost_usd", "triples_count"
    ]
}

def get_database_path():
    """Get the database path, checking environment variables first."""
    # Check environment variable first
    env_path = os.getenv("LLM_EVALUATION_DB_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    
    # Use default path
    dashboard_dir = Path(__file__).parent
    default_path = dashboard_dir / DASHBOARD_CONFIG["default_db_path"]
    return str(default_path)

def get_config_value(section: str, key: str, default=None):
    """Get a configuration value with fallback to default."""
    config_sections = {
        "dashboard": DASHBOARD_CONFIG,
        "metrics": METRICS_CONFIG,
        "charts": CHART_CONFIG,
        "query": QUERY_CONFIG,
        "export": EXPORT_CONFIG
    }
    
    section_config = config_sections.get(section, {})
    return section_config.get(key, default)