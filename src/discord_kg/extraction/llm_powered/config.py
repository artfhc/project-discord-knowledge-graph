"""
Configuration management for the LangGraph-based extraction system.

This module handles all configuration aspects including prompt templates,
LLM provider settings, and workflow parameters.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    CLAUDE = "claude"


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    provider: LLMProvider
    model: Optional[str] = None
    api_key_env_var: str = ""
    default_model: str = ""
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    max_tokens: int = 2000
    temperature: float = 0.1
    
    def __post_init__(self):
        """Set defaults based on provider."""
        if self.provider == LLMProvider.OPENAI:
            self.api_key_env_var = self.api_key_env_var or "OPENAI_API_KEY"
            self.default_model = self.default_model or "gpt-3.5-turbo"
            if not self.input_cost_per_1k:
                self.input_cost_per_1k = 0.0015 if "gpt-3.5" in (self.model or self.default_model) else 0.01
            if not self.output_cost_per_1k:
                self.output_cost_per_1k = 0.002 if "gpt-3.5" in (self.model or self.default_model) else 0.03
        
        elif self.provider == LLMProvider.CLAUDE:
            self.api_key_env_var = self.api_key_env_var or "ANTHROPIC_API_KEY"
            self.default_model = self.default_model or "claude-3-haiku-20240307"
            if not self.input_cost_per_1k:
                self.input_cost_per_1k = 0.00025 if "haiku" in (self.model or self.default_model) else 0.003
            if not self.output_cost_per_1k:
                self.output_cost_per_1k = 0.00125 if "haiku" in (self.model or self.default_model) else 0.015


@dataclass
class WorkflowConfig:
    """Configuration for workflow parameters."""
    batch_size: int = 20
    max_retries: int = 3
    retry_delay_ms: int = 1000
    rate_limit_delay_ms: int = 100
    parallel_processing: bool = False
    max_parallel_nodes: int = 3
    enable_qa_linking: bool = True
    enable_cost_tracking: bool = True
    log_level: str = "INFO"


@dataclass
class PromptTemplate:
    """Single prompt template definition."""
    description: str
    instruction: str
    confidence_score: float = 0.75
    expected_predicates: List[str] = field(default_factory=list)


@dataclass 
class PromptConfig:
    """All prompt templates and system configuration."""
    system_prompt: str
    templates: Dict[str, PromptTemplate] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    predicates: Dict[str, List[str]] = field(default_factory=dict)


class ConfigManager:
    """Central configuration manager for the extraction system."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to YAML configuration file. If None, uses default prompts.yaml
        """
        self.config_path = self._resolve_config_path(config_path)
        self.prompt_config = self._load_prompt_config()
        
    def _resolve_config_path(self, config_path: Optional[str]) -> Path:
        """Resolve the configuration file path."""
        if config_path:
            path = Path(config_path)
            if not path.is_absolute():
                path = Path(__file__).parent / path
        else:
            path = Path(__file__).parent / "prompts.yaml"
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        return path
    
    def _load_prompt_config(self) -> PromptConfig:
        """Load prompt configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            logger.info(f"Loaded configuration from {self.config_path}")
            
            # Parse system prompt
            system_prompt = yaml_data.get('system', {}).get('content', '')
            
            # Parse templates
            templates = {}
            template_data = yaml_data.get('templates', {})
            for name, template_info in template_data.items():
                templates[name] = PromptTemplate(
                    description=template_info.get('description', ''),
                    instruction=template_info.get('instruction', ''),
                    confidence_score=yaml_data.get('config', {}).get('confidence_scores', {}).get(name, 0.75),
                    expected_predicates=yaml_data.get('config', {}).get('predicates', {}).get(name, [])
                )
            
            # Parse configuration
            config_section = yaml_data.get('config', {})
            confidence_scores = config_section.get('confidence_scores', {})
            predicates = config_section.get('predicates', {})
            
            return PromptConfig(
                system_prompt=system_prompt,
                templates=templates,
                confidence_scores=confidence_scores,
                predicates=predicates
            )
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def get_llm_config(
        self, 
        provider: str, 
        model: Optional[str] = None
    ) -> LLMConfig:
        """Create LLM configuration for the specified provider."""
        
        try:
            llm_provider = LLMProvider(provider.lower())
        except ValueError:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
        # Check for model from environment if not provided
        if not model:
            if llm_provider == LLMProvider.OPENAI:
                model = os.getenv("OPENAI_MODEL")
            elif llm_provider == LLMProvider.CLAUDE:
                model = os.getenv("ANTHROPIC_MODEL")
        
        config = LLMConfig(provider=llm_provider, model=model)
        
        # Validate API key is available
        api_key = os.getenv(config.api_key_env_var)
        if not api_key:
            raise ValueError(f"API key not found in environment variable: {config.api_key_env_var}")
        
        logger.info(f"Created LLM config for {provider} with model {config.model or config.default_model}")
        return config
    
    def get_workflow_config(self, **overrides) -> WorkflowConfig:
        """Create workflow configuration with optional overrides."""
        config = WorkflowConfig()
        
        # Apply any provided overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                logger.warning(f"Unknown workflow config parameter: {key}")
        
        return config
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for LLM extraction."""
        return self.prompt_config.system_prompt
    
    def get_template(self, message_type: str) -> PromptTemplate:
        """Get prompt template for a specific message type."""
        template = self.prompt_config.templates.get(message_type)
        if not template:
            raise ValueError(f"No template found for message type: {message_type}")
        return template
    
    def get_confidence_score(self, message_type: str) -> float:
        """Get confidence score for a message type."""
        return self.prompt_config.confidence_scores.get(message_type, 0.75)
    
    def get_predicates(self, message_type: str) -> List[str]:
        """Get expected predicates for a message type."""
        return self.prompt_config.predicates.get(message_type, [])
    
    def format_prompt(self, message_type: str, **kwargs) -> str:
        """Format a prompt template with provided variables."""
        template = self.get_template(message_type)
        try:
            return template.instruction.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing variable for {message_type} template: {e}")
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        logger.info("Reloading configuration...")
        self.prompt_config = self._load_prompt_config()
        logger.info("Configuration reloaded successfully")
    
    def validate_config(self) -> bool:
        """Validate the loaded configuration."""
        errors = []
        
        # Check system prompt
        if not self.prompt_config.system_prompt.strip():
            errors.append("System prompt is empty")
        
        # Check required templates
        required_templates = ['question', 'strategy', 'analysis', 'answer', 'qa_linking']
        for template_name in required_templates:
            if template_name not in self.prompt_config.templates:
                errors.append(f"Missing required template: {template_name}")
            else:
                template = self.prompt_config.templates[template_name]
                if not template.instruction.strip():
                    errors.append(f"Template {template_name} has empty instruction")
        
        # Check confidence scores are valid
        for msg_type, score in self.prompt_config.confidence_scores.items():
            if not 0.0 <= score <= 1.0:
                errors.append(f"Invalid confidence score for {msg_type}: {score}")
        
        if errors:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False
        
        logger.info("Configuration validation passed")
        return True