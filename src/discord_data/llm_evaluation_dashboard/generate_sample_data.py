#!/usr/bin/env python3
"""
Generate sample LLM call data for testing the dashboard.
This creates realistic sample data if no real data exists.
"""

import sqlite3
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from config import get_database_path

def generate_sample_data(num_calls: int = 50):
    """Generate sample LLM call data for testing."""
    
    print(f"🔧 Generating {num_calls} sample LLM calls...")
    
    # Sample data templates
    providers = ["openai", "claude"]
    models = {
        "openai": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
        "claude": ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"]
    }
    
    template_types = ["question", "strategy", "analysis", "answer", "alert", "performance", "discussion"]
    experiments = ["baseline_test", "prompt_optimization_v1", "model_comparison", "cost_analysis"]
    
    sample_messages = [
        {"message_id": "msg_001", "author": "user1", "clean_text": "What's the best trading strategy for volatile markets?"},
        {"message_id": "msg_002", "author": "user2", "clean_text": "I think DCA works well in bear markets"},
        {"message_id": "msg_003", "author": "user3", "clean_text": "My portfolio is up 15% this month using wheel strategy"},
    ]
    
    sample_triples = [
        ["user1", "asks_about", "trading strategies for volatile markets"],
        ["user2", "recommends", "DCA strategy for bear markets"],
        ["user3", "reports_return", "+15% monthly return using wheel strategy"],
    ]
    
    # Connect to database
    db_path = get_database_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    
    # Ensure table exists (copy structure from the real system)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS llm_calls (
            call_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            experiment_name TEXT,
            
            -- Input data
            messages TEXT,
            message_types TEXT,
            batch_size INTEGER,
            segment_id TEXT,
            
            -- Prompt data
            system_prompt TEXT,
            user_prompt TEXT,
            template_type TEXT,
            template_name TEXT,
            
            -- Model metadata
            provider TEXT,
            model_name TEXT,
            temperature REAL,
            max_tokens INTEGER,
            
            -- Output data
            raw_response TEXT,
            parsed_triples TEXT,
            success BOOLEAN,
            error_message TEXT,
            
            -- Performance metrics
            duration_seconds REAL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            total_tokens INTEGER,
            cost_usd REAL,
            
            -- Workflow context
            workflow_step TEXT,
            node_name TEXT,
            workflow_state TEXT
        )
    ''')
    
    # Generate sample calls
    base_time = datetime.now() - timedelta(days=7)
    
    for i in range(num_calls):
        provider = random.choice(providers)
        model = random.choice(models[provider])
        template_type = random.choice(template_types)
        experiment = random.choice(experiments)
        
        # Simulate realistic timing
        call_time = base_time + timedelta(
            days=random.randint(0, 7),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        
        # Simulate realistic metrics based on provider and model
        base_input_tokens = random.randint(50, 500)
        base_output_tokens = random.randint(10, 200)
        
        if provider == "openai":
            if "gpt-4" in model:
                cost_per_1k_input = 0.01
                cost_per_1k_output = 0.03
                base_duration = random.uniform(1.5, 4.0)
            else:  # gpt-3.5
                cost_per_1k_input = 0.0015
                cost_per_1k_output = 0.002
                base_duration = random.uniform(0.8, 2.5)
        else:  # claude
            if "opus" in model:
                cost_per_1k_input = 0.015
                cost_per_1k_output = 0.075
                base_duration = random.uniform(2.0, 5.0)
            elif "sonnet" in model:
                cost_per_1k_input = 0.003
                cost_per_1k_output = 0.015
                base_duration = random.uniform(1.2, 3.5)
            else:  # haiku
                cost_per_1k_input = 0.00025
                cost_per_1k_output = 0.00125
                base_duration = random.uniform(0.5, 1.8)
        
        input_tokens = base_input_tokens + random.randint(-50, 100)
        output_tokens = base_output_tokens + random.randint(-20, 80)
        total_tokens = input_tokens + output_tokens
        
        cost = (input_tokens * cost_per_1k_input / 1000 + 
                output_tokens * cost_per_1k_output / 1000)
        
        duration = base_duration + random.uniform(-0.5, 1.0)
        duration = max(0.1, duration)  # Ensure positive duration
        
        # Success rate varies by complexity
        success_probability = 0.95 if template_type in ["question", "answer"] else 0.85
        success = random.random() < success_probability
        
        # Generate sample content
        messages_data = random.sample(sample_messages, min(3, len(sample_messages)))
        triples_data = random.sample(sample_triples, random.randint(0, 3)) if success else []
        
        system_prompt = f"You are an expert at extracting {template_type} triples from Discord messages."
        user_prompt = f"Extract {template_type} triples from: {json.dumps(messages_data)}"
        raw_response = json.dumps(triples_data) if success else "Error: Unable to parse response"
        
        error_message = None if success else random.choice([
            "Rate limit exceeded", 
            "Invalid JSON response",
            "Token limit exceeded",
            "API timeout"
        ])
        
        # Insert record
        record = {
            'call_id': str(uuid.uuid4()),
            'timestamp': call_time.isoformat(),
            'experiment_name': experiment,
            'messages': json.dumps(messages_data),
            'message_types': json.dumps([template_type]),
            'batch_size': random.randint(1, 20),
            'segment_id': f"segment_{random.randint(1, 10)}",
            'system_prompt': system_prompt,
            'user_prompt': user_prompt,
            'template_type': template_type,
            'template_name': f"{template_type}_template",
            'provider': provider,
            'model_name': model,
            'temperature': 0.1,
            'max_tokens': 2000,
            'raw_response': raw_response,
            'parsed_triples': json.dumps(triples_data) if triples_data else None,
            'success': 1 if success else 0,
            'error_message': error_message,
            'duration_seconds': duration,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'cost_usd': cost,
            'workflow_step': f"{template_type}_extraction",
            'node_name': f"extract_{template_type}_node",
            'workflow_state': None
        }
        
        columns = ', '.join(record.keys())
        placeholders = ', '.join(['?' for _ in record])
        
        conn.execute(
            f'INSERT INTO llm_calls ({columns}) VALUES ({placeholders})',
            list(record.values())
        )
    
    conn.commit()
    conn.close()
    
    print(f"✅ Generated {num_calls} sample LLM calls")
    print(f"📊 Data saved to: {db_path}")
    print(f"\n🚀 Now you can test the dashboard:")
    print(f"   ./run_dashboard.sh")

if __name__ == "__main__":
    import sys
    
    num_calls = 50
    if len(sys.argv) > 1:
        try:
            num_calls = int(sys.argv[1])
        except ValueError:
            print("Usage: python generate_sample_data.py [num_calls]")
            sys.exit(1)
    
    generate_sample_data(num_calls)