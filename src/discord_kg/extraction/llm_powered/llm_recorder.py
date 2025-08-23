"""
LLM Call Recording System for Discord Knowledge Graph Extraction

This module provides comprehensive recording of all LLM API calls for evaluation
and prompt optimization. Integrates seamlessly with the existing LangGraph workflow.
"""

import json
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMCallRecord:
    """Comprehensive record of a single LLM API call."""
    
    # Unique identifiers
    call_id: str
    timestamp: str
    experiment_name: Optional[str] = None
    
    # Input data
    messages: List[Dict[str, Any]] = None
    message_types: List[str] = None
    batch_size: int = 0
    segment_id: Optional[str] = None
    
    # Prompt data
    system_prompt: str = ""
    user_prompt: str = ""
    template_type: str = ""
    template_name: str = ""
    
    # Model metadata
    provider: str = ""
    model_name: str = ""
    temperature: float = 0.1
    max_tokens: int = 2000
    
    # Output data
    raw_response: str = ""
    parsed_triples: List[List[str]] = None
    success: bool = True
    error_message: Optional[str] = None
    
    # Parsing status
    parsing_success: bool = True
    parsing_error: Optional[str] = None
    triples_count: int = 0
    reasoning: Optional[str] = None
    
    # Performance metrics
    duration_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    
    # Workflow context
    workflow_step: str = ""
    node_name: str = ""
    workflow_state: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)


class LLMCallStorage:
    """SQLite-based storage for LLM call records."""
    
    def __init__(self, db_path: str = "bin/llm_evaluation/llm_calls.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS llm_calls (
                    call_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    experiment_name TEXT,
                    
                    -- Input data
                    messages TEXT,  -- JSON
                    message_types TEXT,  -- JSON array
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
                    parsed_triples TEXT,  -- JSON
                    success BOOLEAN,
                    error_message TEXT,
                    
                    -- Parsing status
                    parsing_success BOOLEAN DEFAULT TRUE,
                    parsing_error TEXT,
                    triples_count INTEGER DEFAULT 0,
                    reasoning TEXT,
                    
                    -- Performance metrics
                    duration_seconds REAL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    total_tokens INTEGER,
                    cost_usd REAL,
                    
                    -- Workflow context
                    workflow_step TEXT,
                    node_name TEXT,
                    workflow_state TEXT  -- JSON
                )
            ''')
            
            # Migrate existing database to add new columns if they don't exist
            try:
                conn.execute('ALTER TABLE llm_calls ADD COLUMN parsing_success BOOLEAN DEFAULT TRUE')
            except:
                pass  # Column already exists
            
            try:
                conn.execute('ALTER TABLE llm_calls ADD COLUMN parsing_error TEXT')
            except:
                pass  # Column already exists
                
            try:
                conn.execute('ALTER TABLE llm_calls ADD COLUMN triples_count INTEGER DEFAULT 0')
            except:
                pass  # Column already exists
                
            try:
                conn.execute('ALTER TABLE llm_calls ADD COLUMN reasoning TEXT')
            except:
                pass  # Column already exists
            
            # Create indexes for common queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON llm_calls(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_provider ON llm_calls(provider)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_template_type ON llm_calls(template_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_experiment ON llm_calls(experiment_name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_success ON llm_calls(success)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_parsing_success ON llm_calls(parsing_success)')
            
            conn.commit()
    
    def store_call(self, record: LLMCallRecord):
        """Store a call record in the database."""
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    data = record.to_dict()
                    
                    # Convert complex types to JSON strings
                    data['messages'] = json.dumps(data['messages']) if data['messages'] else None
                    data['message_types'] = json.dumps(data['message_types']) if data['message_types'] else None
                    data['parsed_triples'] = json.dumps(data['parsed_triples']) if data['parsed_triples'] else None
                    data['workflow_state'] = json.dumps(data['workflow_state']) if data['workflow_state'] else None
                    
                    columns = ', '.join(data.keys())
                    placeholders = ', '.join(['?' for _ in data])
                    
                    conn.execute(
                        f'INSERT OR REPLACE INTO llm_calls ({columns}) VALUES ({placeholders})',
                        list(data.values())
                    )
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Failed to store LLM call record: {e}")
    
    def get_calls(self, 
                  provider: Optional[str] = None,
                  template_type: Optional[str] = None, 
                  experiment_name: Optional[str] = None,
                  limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve call records with optional filtering."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = "SELECT * FROM llm_calls WHERE 1=1"
                params = []
                
                if provider:
                    query += " AND provider = ?"
                    params.append(provider)
                
                if template_type:
                    query += " AND template_type = ?"
                    params.append(template_type)
                
                if experiment_name:
                    query += " AND experiment_name = ?"
                    params.append(experiment_name)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to retrieve LLM call records: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basic statistics about recorded calls."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_calls,
                        COUNT(CASE WHEN success = 1 THEN 1 END) as successful_calls,
                        SUM(cost_usd) as total_cost,
                        AVG(duration_seconds) as avg_duration,
                        SUM(total_tokens) as total_tokens
                    FROM llm_calls
                ''')
                
                row = cursor.fetchone()
                return {
                    'total_calls': row[0] or 0,
                    'successful_calls': row[1] or 0,
                    'total_cost_usd': round(row[2] or 0, 4),
                    'avg_duration_seconds': round(row[3] or 0, 3),
                    'total_tokens': row[4] or 0,
                    'success_rate': round((row[1] or 0) / max(1, row[0] or 1) * 100, 2)
                }
                
        except Exception as e:
            logger.error(f"Failed to get LLM call stats: {e}")
            return {}


# Global storage instance
_storage = None
_recording_enabled = False
_experiment_name = None


def get_storage() -> LLMCallStorage:
    """Get or create the global storage instance."""
    global _storage
    if _storage is None:
        _storage = LLMCallStorage()
    return _storage


def enable_recording(experiment_name: Optional[str] = None):
    """Enable LLM call recording globally."""
    global _recording_enabled, _experiment_name
    _recording_enabled = True
    _experiment_name = experiment_name
    logger.info(f"LLM call recording enabled (experiment: {experiment_name})")


def disable_recording():
    """Disable LLM call recording globally."""
    global _recording_enabled, _experiment_name
    _recording_enabled = False
    _experiment_name = None
    logger.info("LLM call recording disabled")


def is_recording_enabled() -> bool:
    """Check if recording is currently enabled."""
    return _recording_enabled


@contextmanager
def record_llm_call(
    messages: List[Dict[str, Any]] = None,
    template_type: str = "",
    template_name: str = "",
    provider: str = "",
    model_name: str = "",
    workflow_step: str = "",
    node_name: str = "",
    **kwargs
):
    """Context manager for recording LLM calls."""
    
    if not _recording_enabled:
        # Recording disabled, just yield
        record = None
        yield record
        return
    
    # Initialize record
    record = LLMCallRecord(
        call_id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        experiment_name=_experiment_name,
        messages=messages,
        message_types=[msg.get('type', 'unknown') for msg in messages] if messages else [],
        batch_size=len(messages) if messages else 0,
        template_type=template_type,
        template_name=template_name,
        provider=provider,
        model_name=model_name,
        workflow_step=workflow_step,
        node_name=node_name,
        **kwargs
    )
    
    # Start timing
    start_time = time.time()
    
    try:
        yield record
        record.success = True
    except Exception as e:
        record.success = False
        record.error_message = str(e)
        raise
    finally:
        # Calculate duration
        record.duration_seconds = time.time() - start_time
        
        # Store the record
        try:
            storage = get_storage()
            storage.store_call(record)
        except Exception as e:
            logger.error(f"Failed to record LLM call: {e}")


def record_call_manually(record: LLMCallRecord):
    """Manually record an LLM call."""
    if _recording_enabled:
        try:
            storage = get_storage()
            storage.store_call(record)
        except Exception as e:
            logger.error(f"Failed to manually record LLM call: {e}")


def get_call_stats() -> Dict[str, Any]:
    """Get statistics about recorded calls."""
    try:
        storage = get_storage()
        return storage.get_stats()
    except Exception as e:
        logger.error(f"Failed to get call stats: {e}")
        return {}


def export_calls_to_csv(filename: str, **filters):
    """Export call records to CSV file."""
    try:
        import pandas as pd
        storage = get_storage()
        calls = storage.get_calls(limit=10000, **filters)
        
        if calls:
            df = pd.DataFrame(calls)
            df.to_csv(filename, index=False)
            logger.info(f"Exported {len(calls)} LLM call records to {filename}")
        else:
            logger.warning("No LLM call records found to export")
            
    except ImportError:
        logger.error("pandas not installed - cannot export to CSV")
    except Exception as e:
        logger.error(f"Failed to export calls to CSV: {e}")


def update_latest_record_reasoning(reasoning: str):
    """Update the most recent record with reasoning information."""
    if not _recording_enabled:
        return
    
    try:
        storage = get_storage()
        with sqlite3.connect(storage.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE llm_calls 
                SET reasoning = ?
                WHERE call_id = (
                    SELECT call_id 
                    FROM llm_calls 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                )
            """, (reasoning,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database error updating reasoning: {e}")
    except Exception as e:
        logger.error(f"Unexpected error updating reasoning: {e}")