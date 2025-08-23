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
    
    This wraps BaseLLMProvider.extract_triples to add recording while maintaining
    the existing interface and workflow compatibility.
    """
    try:
        # Import the recording modules
        from llm_recorder import record_llm_call
        
        # Get the existing modules
        import llm_providers
        from llm_providers import BaseLLMProvider
        
        # Store the original extract_triples method
        original_extract_triples = BaseLLMProvider.extract_triples
        
        def recorded_extract_triples(self, system_prompt: str, user_prompt: str, max_retries: int = 3):
            """
            Enhanced extract_triples method with integrated recording.
            
            This wrapper maintains the original interface while adding comprehensive
            recording of all LLM calls made through the normal workflow.
            """
            # Extract context information from the prompts for better recording
            template_type = "unknown"
            workflow_step = "extraction"
            
            # Infer template type from user prompt content (which contains the specific instructions)
            user_lower = user_prompt.lower()
            if "question triples" in user_lower or "asks_about" in user_lower:
                template_type = "question"
            elif "strategy" in user_lower or "strategy triples" in user_lower:
                template_type = "strategy"
            elif "analysis triples" in user_lower or "analyzes" in user_lower:
                template_type = "analysis"
            elif "answer messages" in user_lower or "information-providing triples" in user_lower or "provides_info" in user_lower:
                template_type = "answer"
            elif "discussion triples" in user_lower or "conversation messages" in user_lower:
                template_type = "discussion"
            elif "performance triples" in user_lower or "reports_return" in user_lower:
                template_type = "performance"
            elif "alert triples" in user_lower or "alerts" in user_lower:
                template_type = "alert"
            elif "linking" in user_lower or "connect" in user_lower or "answered_by" in user_lower:
                template_type = "qa_linking"
                workflow_step = "qa_linking"
            
            # Create mock messages list for recording (since we don't have access to the original messages here)
            # We'll extract what we can from the user prompt
            mock_messages = [{
                'message_id': f'extracted_from_prompt_{hash(user_prompt) % 10000}',
                'author': 'extracted_context',
                'text': user_prompt[:200] + '...' if len(user_prompt) > 200 else user_prompt,
                'timestamp': None,
                'segment_id': f'segment_{hash(system_prompt) % 1000}'
            }]
            
            # Use recording context manager
            with record_llm_call(
                messages=mock_messages,
                template_type=template_type,
                template_name=f"{template_type}_template",
                provider=self.config.provider.value,
                model_name=self.config.model or self.config.default_model,
                workflow_step=workflow_step,
                node_name=f"extract_{template_type}_node",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                segment_id=mock_messages[0]['segment_id']
            ) as record:
                
                try:
                    # Call the original method
                    response = original_extract_triples(self, system_prompt, user_prompt, max_retries)
                    
                    # Update recording with response data
                    if record:
                        record.input_tokens = response.input_tokens
                        record.output_tokens = response.output_tokens
                        record.total_tokens = response.total_tokens
                        record.cost_usd = response.cost
                        record.raw_response = response.content
                        record.success = response.success
                        record.error_message = response.error
                        
                        # Try to parse triples from the response
                        if response.success:
                            try:
                                import json
                                parsed_triples = json.loads(response.content)
                                if isinstance(parsed_triples, list):
                                    record.parsed_triples = parsed_triples
                                else:
                                    record.parsed_triples = []
                            except json.JSONDecodeError:
                                record.parsed_triples = []
                        else:
                            record.parsed_triples = []
                    
                    return response
                    
                except Exception as e:
                    # Update record with error info
                    if record:
                        record.success = False
                        record.error_message = str(e)
                    
                    # Re-raise the exception to maintain original behavior
                    raise
        
        # Apply the monkey patch
        BaseLLMProvider.extract_triples = recorded_extract_triples
        
        print("✅ BaseLLMProvider.extract_triples patched with recording capabilities")
        return True
        
    except Exception as e:
        print(f"❌ Failed to patch LLM providers: {e}")
        import traceback
        traceback.print_exc()
        return False


def enable_recording_in_extractor_langgraph(experiment_name: str = None):
    """
    Enable recording in the LangGraph extractor with minimal code changes.
    
    This function:
    1. Enables the recording system with the specified experiment name
    2. Monkey-patches BaseLLMProvider.extract_triples to add recording
    3. Maintains full compatibility with existing workflow
    
    Usage:
        from enable_recording import enable_recording_in_extractor_langgraph
        enable_recording_in_extractor_langgraph("my_experiment")
        
        # Now run your normal extraction workflow
        result = workflow.run(messages)
    """
    try:
        # Enable recording system
        from llm_recorder import enable_recording
        enable_recording(experiment_name)
        
        # Apply monkey patches to the actual interface being used
        patch_success = patch_llm_providers_with_recording()
        
        if patch_success:
            print(f"🎉 LLM call recording enabled for experiment: {experiment_name or 'default'}")
            print("📊 All LLM calls through BaseLLMProvider.extract_triples will be recorded")
            print("📁 Recording data saved to: bin/llm_evaluation/llm_calls.db")
            return True
        else:
            print("❌ Failed to enable recording - check that llm_providers module is importable")
            return False
            
    except Exception as e:
        print(f"❌ Error enabling recording: {e}")
        import traceback
        traceback.print_exc()
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