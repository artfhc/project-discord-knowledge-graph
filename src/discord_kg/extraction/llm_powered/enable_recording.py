"""
Easy integration patch to enable LLM call recording in existing LangGraph workflow.

This module provides minimal changes to enable comprehensive recording
in your existing extractor_langgraph.py workflow.
"""

import sys
import os
from pathlib import Path

def patch_llm_providers_with_recording():
    """
    Monkey-patch the existing LLM providers to include recording capabilities.
    
    This allows enabling recording without changing the existing codebase.
    """
    try:
        # Import the recording modules
        from llm_recorder import record_llm_call
        from recorded_llm_providers import RecordedLLMClient
        
        # Get the existing modules
        import llm_providers
        
        # Store original classes
        original_llm_client = None
        if hasattr(llm_providers, 'LLMClient'):
            # For the original extractor_llm.py
            original_llm_client = llm_providers.LLMClient
            
            # Replace with recorded version
            llm_providers.LLMClient = RecordedLLMClient
            
        # Also patch any factory methods
        if hasattr(llm_providers, 'LLMProviderFactory'):
            original_create = llm_providers.LLMProviderFactory.create_from_string
            
            def create_recorded_provider(provider_name, model=None):
                """Enhanced factory method that creates recorded providers."""
                return RecordedLLMClient(provider_name, model)
            
            llm_providers.LLMProviderFactory.create_from_string = staticmethod(create_recorded_provider)
        
        print("✅ LLM providers patched with recording capabilities")
        return True
        
    except Exception as e:
        print(f"❌ Failed to patch LLM providers: {e}")
        return False


def enable_recording_in_extractor_langgraph(experiment_name: str = None):
    """
    Enable recording in the LangGraph extractor with minimal code changes.
    
    Usage:
        from enable_recording import enable_recording_in_extractor_langgraph
        enable_recording_in_extractor_langgraph("my_experiment")
        
        # Now run your normal extraction
        result = workflow.run(messages)
    """
    try:
        # Enable recording
        from llm_recorder import enable_recording
        enable_recording(experiment_name)
        
        # Patch the providers
        patch_success = patch_llm_providers_with_recording()
        
        if patch_success:
            print(f"🎉 LLM call recording enabled for experiment: {experiment_name}")
            print("📊 All LLM calls will now be recorded to bin/llm_evaluation/")
            return True
        else:
            print("❌ Failed to enable recording")
            return False
            
    except Exception as e:
        print(f"❌ Error enabling recording: {e}")
        return False


def show_recording_stats():
    """Display current recording statistics."""
    try:
        from llm_recorder import get_call_stats
        stats = get_call_stats()
        
        print("\n📊 LLM Call Recording Statistics:")
        print(f"   • Total calls: {stats.get('total_calls', 0)}")
        print(f"   • Success rate: {stats.get('success_rate', 0)}%")
        print(f"   • Total cost: ${stats.get('total_cost_usd', 0)}")
        print(f"   • Total tokens: {stats.get('total_tokens', 0):,}")
        print(f"   • Avg duration: {stats.get('avg_duration_seconds', 0):.3f}s")
        
    except Exception as e:
        print(f"❌ Error getting recording stats: {e}")


def export_recorded_data(filename: str = "llm_calls_export.csv", **filters):
    """Export recorded LLM call data to CSV."""
    try:
        from llm_recorder import export_calls_to_csv
        export_calls_to_csv(filename, **filters)
        print(f"✅ Exported LLM call data to {filename}")
        
    except Exception as e:
        print(f"❌ Error exporting data: {e}")


def create_simple_analysis_script():
    """Create a simple Python script for analyzing recorded data."""
    
    analysis_script = '''#!/usr/bin/env python3
"""
Simple analysis script for LLM call recordings.
Run this script to analyze your recorded LLM calls.
"""

import sqlite3
import pandas as pd
from pathlib import Path

# Connect to the database
db_path = "bin/llm_evaluation/llm_calls.db"
if not Path(db_path).exists():
    print(f"❌ No recording database found at {db_path}")
    print("   Make sure you've run some extractions with recording enabled.")
    exit(1)

conn = sqlite3.connect(db_path)

print("📊 LLM Call Analysis Report")
print("=" * 50)

# Basic stats
print("\\n1. Overall Statistics:")
stats = pd.read_sql_query("""
    SELECT 
        COUNT(*) as total_calls,
        COUNT(CASE WHEN success = 1 THEN 1 END) as successful_calls,
        ROUND(AVG(duration_seconds), 3) as avg_duration,
        ROUND(SUM(cost_usd), 4) as total_cost,
        SUM(total_tokens) as total_tokens
    FROM llm_calls
""", conn)

print(f"   • Total API calls: {stats['total_calls'].iloc[0]}")
print(f"   • Successful calls: {stats['successful_calls'].iloc[0]}")
print(f"   • Success rate: {stats['successful_calls'].iloc[0] / max(1, stats['total_calls'].iloc[0]) * 100:.1f}%")
print(f"   • Total cost: ${stats['total_cost'].iloc[0]}")
print(f"   • Average duration: {stats['avg_duration'].iloc[0]}s")
print(f"   • Total tokens: {stats['total_tokens'].iloc[0]:,}")

# Provider comparison
print("\\n2. Provider Comparison:")
providers = pd.read_sql_query("""
    SELECT 
        provider,
        COUNT(*) as calls,
        ROUND(AVG(duration_seconds), 3) as avg_duration,
        ROUND(SUM(cost_usd), 4) as total_cost,
        ROUND(AVG(cost_usd), 6) as avg_cost_per_call
    FROM llm_calls 
    GROUP BY provider
""", conn)

for _, row in providers.iterrows():
    print(f"   • {row['provider'].upper()}:")
    print(f"     - Calls: {row['calls']}")
    print(f"     - Avg duration: {row['avg_duration']}s")
    print(f"     - Total cost: ${row['total_cost']}")
    print(f"     - Avg cost/call: ${row['avg_cost_per_call']}")

# Template performance
print("\\n3. Template Performance:")
templates = pd.read_sql_query("""
    SELECT 
        template_type,
        COUNT(*) as calls,
        COUNT(CASE WHEN success = 1 THEN 1 END) as successful,
        ROUND(AVG(duration_seconds), 3) as avg_duration
    FROM llm_calls 
    WHERE template_type != ''
    GROUP BY template_type
    ORDER BY calls DESC
""", conn)

for _, row in templates.iterrows():
    success_rate = row['successful'] / max(1, row['calls']) * 100
    print(f"   • {row['template_type']}:")
    print(f"     - Calls: {row['calls']}")
    print(f"     - Success rate: {success_rate:.1f}%")
    print(f"     - Avg duration: {row['avg_duration']}s")

# Recent failures
print("\\n4. Recent Failures (if any):")
failures = pd.read_sql_query("""
    SELECT template_type, error_message, timestamp
    FROM llm_calls 
    WHERE success = 0 
    ORDER BY timestamp DESC 
    LIMIT 5
""", conn)

if len(failures) > 0:
    for _, row in failures.iterrows():
        print(f"   • {row['timestamp']}: {row['template_type']} - {row['error_message']}")
else:
    print("   ✅ No recent failures found!")

conn.close()
print("\\n" + "=" * 50)
print("💡 Tip: You can also export data to CSV for deeper analysis:")
print("   python -c \\"from enable_recording import export_recorded_data; export_recorded_data()\\"")
'''
    
    with open("analyze_recordings.py", "w") as f:
        f.write(analysis_script)
    
    os.chmod("analyze_recordings.py", 0o755)
    print("✅ Created analysis script: analyze_recordings.py")
    print("   Run it with: python analyze_recordings.py")


if __name__ == "__main__":
    """Command-line interface for recording utilities."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM Call Recording Utilities")
    parser.add_argument("--enable", metavar="EXPERIMENT_NAME", 
                       help="Enable recording for the given experiment")
    parser.add_argument("--stats", action="store_true", 
                       help="Show recording statistics")
    parser.add_argument("--export", metavar="FILENAME", 
                       help="Export recorded data to CSV file")
    parser.add_argument("--create-analysis", action="store_true",
                       help="Create analysis script")
    
    args = parser.parse_args()
    
    if args.enable:
        enable_recording_in_extractor_langgraph(args.enable)
    elif args.stats:
        show_recording_stats()
    elif args.export:
        export_recorded_data(args.export)
    elif args.create_analysis:
        create_simple_analysis_script()
    else:
        parser.print_help()