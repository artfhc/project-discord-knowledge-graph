"""
LangGraph-based Discord Knowledge Graph Triple Extraction System.

This package provides a redesigned architecture for extracting structured knowledge
triples from Discord conversations using LangGraph for workflow orchestration.

Key improvements over the original system:
- Modular node-based architecture with clear separation of concerns
- Proper workflow orchestration with conditional routing
- Enhanced error handling and retry logic
- Better cost tracking and analytics
- Extensible design for new message types and extraction methods
- Comprehensive configuration management

Main Components:
- workflow_state: Type-safe state management for the workflow
- config: Centralized configuration management
- llm_providers: Abstracted LLM provider interfaces
- nodes: Individual processing nodes for each workflow step
- workflow: Main LangGraph workflow orchestration
- extractor_langgraph: CLI interface and high-level API

Usage:
    from discord_kg.extraction.llm_powered import ExtractionWorkflow
    
    workflow = ExtractionWorkflow(llm_provider="openai", batch_size=20)
    result = workflow.run(messages)
"""

from .workflow import ExtractionWorkflow, run_extraction_pipeline
from .workflow_state import (
    WorkflowState, Triple, ProcessingMetrics, NodeResult,
    ProcessingStatus, MessageType, create_initial_state
)
from .config import ConfigManager, LLMConfig, WorkflowConfig
from .llm_providers import LLMProviderFactory, TripleExtractor

__version__ = "2.0.0"
__author__ = "Claude Code Assistant"

__all__ = [
    # Main interfaces
    "ExtractionWorkflow",
    "run_extraction_pipeline",
    
    # State and data structures
    "WorkflowState", 
    "Triple",
    "ProcessingMetrics",
    "NodeResult",
    "ProcessingStatus",
    "MessageType",
    "create_initial_state",
    
    # Configuration
    "ConfigManager",
    "LLMConfig", 
    "WorkflowConfig",
    
    # LLM providers
    "LLMProviderFactory",
    "TripleExtractor",
]