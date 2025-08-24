"""
LLM provider abstractions for OpenAI and Claude APIs.

This module provides a unified interface for different LLM providers,
handling API calls, cost tracking, and response formatting.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field

try:
    # Try relative imports first (when used as package)
    from .config import LLMConfig, LLMProvider
    from .workflow_state import ProcessingMetrics
except ImportError:
    # Fall back to direct imports (when running as script)
    from config import LLMConfig, LLMProvider
    from workflow_state import ProcessingMetrics

def get_logger():
    """Get logger safely, creating it if needed."""
    return logging.getLogger(__name__ or 'llm_providers')


@dataclass
class LLMResponse:
    """Standardized response from LLM providers."""
    content: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    model: str
    provider: str
    error: Optional[str] = None
    reasoning: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """Check if the response was successful."""
        return self.error is None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: LLMConfig):
        """Initialize the provider with configuration."""
        self.config = config
        self.total_cost = 0.0
        self.total_tokens = 0
        self.request_count = 0
        self.client = None
        self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize the API client."""
        pass
    
    @abstractmethod
    def _make_api_call(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Make the actual API call to the provider."""
        pass
    
    def extract_triples(
        self, 
        system_prompt: str, 
        user_prompt: str,
        max_retries: int = 3
    ) -> LLMResponse:
        """
        Extract triples using the LLM with retry logic.
        
        Args:
            system_prompt: System prompt defining the task
            user_prompt: User prompt with the data to process
            max_retries: Maximum number of retry attempts
            
        Returns:
            LLMResponse with the extraction results
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                self.request_count += 1
                
                # Make API call
                response = self._make_api_call(system_prompt, user_prompt)
                
                # Calculate cost
                input_tokens = response.get('usage', {}).get('prompt_tokens', 0)
                output_tokens = response.get('usage', {}).get('completion_tokens', 0)
                total_tokens = input_tokens + output_tokens
                
                cost = (
                    input_tokens * self.config.input_cost_per_1k / 1000 +
                    output_tokens * self.config.output_cost_per_1k / 1000
                )
                
                # Update tracking
                self.total_cost += cost
                self.total_tokens += total_tokens
                
                get_logger().debug(
                    f"Request {self.request_count}: {input_tokens}+{output_tokens} tokens, "
                    f"${cost:.4f}, attempt {attempt + 1}"
                )
                
                return LLMResponse(
                    content=response.get('content', ''),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    model=self.config.model or self.config.default_model,
                    provider=self.config.provider.value
                )
                
            except Exception as e:
                last_error = str(e)
                get_logger().warning(f"API call failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                
                if attempt < max_retries:
                    # Exponential backoff
                    delay = (2 ** attempt) * self.config.temperature
                    time.sleep(delay)
                    continue
                else:
                    break
        
        # All retries failed
        get_logger().error(f"All API call attempts failed. Last error: {last_error}")
        return LLMResponse(
            content="[]",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            cost=0.0,
            model=self.config.model or self.config.default_model,
            provider=self.config.provider.value,
            error=last_error
        )
    
    def get_metrics(self) -> ProcessingMetrics:
        """Get current processing metrics."""
        return ProcessingMetrics(
            api_calls=self.request_count,
            total_tokens=self.total_tokens,
            total_cost=self.total_cost
        )
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get detailed cost summary."""
        return {
            "total_requests": self.request_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "avg_cost_per_request": round(self.total_cost / max(1, self.request_count), 4),
            "provider": self.config.provider.value,
            "model": self.config.model or self.config.default_model,
            "input_cost_per_1k": self.config.input_cost_per_1k,
            "output_cost_per_1k": self.config.output_cost_per_1k
        }


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider implementation."""
    
    def _initialize_client(self):
        """Initialize OpenAI client."""
        try:
            import openai
            import os
            
            api_key = os.getenv(self.config.api_key_env_var)
            if not api_key:
                raise ValueError(f"API key not found: {self.config.api_key_env_var}")
            
            self.client = openai.OpenAI(api_key=api_key)
            model_name = self.config.model or self.config.default_model
            
            get_logger().info(f"Initialized OpenAI client with model: {model_name}")
            
        except ImportError:
            raise ImportError("OpenAI library not installed. Run: pip install openai")
    
    def _make_api_call(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Make OpenAI API call."""
        response = self.client.chat.completions.create(
            model=self.config.model or self.config.default_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        return {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        }


class ClaudeProvider(BaseLLMProvider):
    """Claude API provider implementation."""
    
    def _initialize_client(self):
        """Initialize Claude client."""
        try:
            import anthropic
            import os
            
            api_key = os.getenv(self.config.api_key_env_var)
            if not api_key:
                raise ValueError(f"API key not found: {self.config.api_key_env_var}")
            
            self.client = anthropic.Anthropic(api_key=api_key)
            model_name = self.config.model or self.config.default_model
            
            get_logger().info(f"Initialized Claude client with model: {model_name}")
            
        except ImportError:
            raise ImportError("Anthropic library not installed. Run: pip install anthropic")
    
    def _make_api_call(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Make Claude API call."""
        response = self.client.messages.create(
            model=self.config.model or self.config.default_model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        return {
            "content": response.content[0].text,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens
            }
        }


class LLMProviderFactory:
    """Factory for creating LLM providers."""
    
    @staticmethod
    def create_provider(config: LLMConfig) -> BaseLLMProvider:
        """Create an LLM provider based on configuration."""
        
        if config.provider == LLMProvider.OPENAI:
            return OpenAIProvider(config)
        elif config.provider == LLMProvider.CLAUDE:
            return ClaudeProvider(config)
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")
    
    @staticmethod
    def create_from_string(
        provider_name: str, 
        model: Optional[str] = None
    ) -> BaseLLMProvider:
        """Create provider from string name."""
        try:
            from .config import ConfigManager
        except ImportError:
            from config import ConfigManager
        
        config_manager = ConfigManager()
        llm_config = config_manager.get_llm_config(provider_name, model)
        return LLMProviderFactory.create_provider(llm_config)


class TripleExtractor:
    """High-level triple extraction interface using LLM providers."""
    
    def __init__(self, provider: BaseLLMProvider):
        """Initialize with an LLM provider."""
        self.provider = provider
    
    def extract_from_messages(
        self, 
        messages: List[Dict[str, Any]], 
        system_prompt: str,
        user_prompt_template: str
    ) -> List[Dict[str, Any]]:
        """
        Extract triples from a list of messages.
        
        Args:
            messages: List of message dictionaries
            system_prompt: System prompt for the LLM
            user_prompt_template: Template for user prompt (should accept message_text)
            
        Returns:
            List of extracted triples
        """
        # Format messages for prompt
        message_text = "\n".join([
            f"Author: {msg['author']}, Text: {msg.get('clean_text', msg.get('text', ''))}"
            for msg in messages
        ])
        
        user_prompt = user_prompt_template.format(message_text=message_text)
        
        # Extract triples
        response = self.provider.extract_triples(system_prompt, user_prompt)
        
        if not response.success:
            get_logger().error(f"Triple extraction failed: {response.error}")
            return []
        
        # Parse JSON response
        try:
            triples = json.loads(response.content)
            if not isinstance(triples, list):
                get_logger().warning("LLM returned non-list response")
                return []
            
            return triples
        
        except json.JSONDecodeError as e:
            get_logger().warning(f"Failed to parse LLM response as JSON: {e}")
            get_logger().debug(f"Response content: {response.content[:200]}")
            return []
    
    def extract_qa_links(
        self, 
        questions: List[Dict[str, Any]], 
        answers: List[Dict[str, Any]],
        system_prompt: str,
        linking_prompt_template: str
    ) -> List[Dict[str, Any]]:
        """
        Extract Q&A links between questions and answers.
        
        Args:
            questions: List of question messages
            answers: List of answer messages
            system_prompt: System prompt for the LLM
            linking_prompt_template: Template for linking prompt
            
        Returns:
            List of Q&A linking triples
        """
        if not questions or not answers:
            return []
        
        # Format questions and answers
        q_text = "\n".join([
            f"Q{i}: {q['message_id']} - {q['author']}: {q.get('clean_text', q.get('text', ''))}"
            for i, q in enumerate(questions)
        ])
        
        a_text = "\n".join([
            f"A{i}: {a['message_id']} - {a['author']}: {a.get('clean_text', a.get('text', ''))}"
            for i, a in enumerate(answers)
        ])
        
        user_prompt = linking_prompt_template.format(q_text=q_text, a_text=a_text)
        
        # Extract links
        response = self.provider.extract_triples(system_prompt, user_prompt)
        
        if not response.success:
            get_logger().error(f"Q&A linking failed: {response.error}")
            return []
        
        # Parse and validate links with reasoning extraction
        try:
            content = response.content
            
            # Extract JSON between markers
            json_start = content.find("JSON_START")
            json_end = content.find("JSON_END")
            
            if json_start != -1 and json_end != -1:
                # Extract JSON content
                json_content = content[json_start + len("JSON_START"):json_end].strip()
                links = json.loads(json_content)
                
                # Extract reasoning if present
                reasoning_start = content.find("REASONING:")
                reasoning = ""
                if reasoning_start != -1:
                    reasoning = content[reasoning_start + len("REASONING:"):].strip()
                
                # Store reasoning in response object for recording
                if reasoning and hasattr(response, '__dict__'):
                    response.reasoning = reasoning
                    
                    # Also try to update the most recent database record with reasoning
                    try:
                        # Try relative import first
                        try:
                            from .llm_recorder import update_latest_record_reasoning
                        except ImportError:
                            # Fall back to direct import
                            from llm_recorder import update_latest_record_reasoning
                        
                        update_latest_record_reasoning(reasoning)
                    except ImportError:
                        pass  # Recording not available
                    except Exception as e:
                        get_logger().debug(f"Failed to update reasoning in database: {e}")
                
                # Log first part of reasoning for debugging
                if reasoning:
                    get_logger().info(f"Q&A linking reasoning extracted: {len(reasoning)} characters")
                    
            else:
                # Fallback to old parsing method for backward compatibility
                get_logger().warning("Q&A linking response missing JSON markers, trying direct JSON parse")
                links = json.loads(content)
            
            if not isinstance(links, list):
                return []
            
            # Filter for valid Q&A links
            valid_links = []
            for link in links:
                if (len(link) == 3 and 
                    link[1] == "answered_by" and
                    isinstance(link[0], str) and 
                    isinstance(link[2], str)):
                    valid_links.append(link)
            
            return valid_links
        
        except json.JSONDecodeError as e:
            get_logger().warning(f"Failed to parse Q&A linking response as JSON: {e}")
            # Log the raw content to help debug parsing issues
            get_logger().debug(f"Raw Q&A linking response: {response.content[:500]}...")
            return []