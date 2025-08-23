"""
Enhanced LLM Providers with Integrated Call Recording

This module provides drop-in replacements for the existing LLM providers
that automatically record all API calls for evaluation and analysis.
"""

import json
import time
import os
from typing import Dict, Any, List, Optional
from llm_recorder import record_llm_call, LLMCallRecord, is_recording_enabled


class RecordedLLMClient:
    """Enhanced LLM client with integrated call recording."""
    
    def __init__(self, provider: str = "openai", model: str = None):
        self.provider = provider.lower()
        self.total_cost = 0.0
        self.total_tokens = 0
        self.request_count = 0
        
        if self.provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.model = model or os.getenv("OPENAI_MODEL") or "gpt-3.5-turbo"
                # Pricing per 1K tokens (as of 2024)
                self.input_cost_per_1k = 0.0015 if "gpt-3.5" in self.model else 0.01
                self.output_cost_per_1k = 0.002 if "gpt-3.5" in self.model else 0.03
            except ImportError:
                raise ImportError("OpenAI library not installed. Run: pip install openai")
                
        elif self.provider == "claude":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                self.model = model or os.getenv("ANTHROPIC_MODEL") or "claude-3-haiku-20240307"
                # Pricing per 1K tokens for Claude
                self.input_cost_per_1k = 0.00025 if "haiku" in self.model else 0.003
                self.output_cost_per_1k = 0.00125 if "haiku" in self.model else 0.015
            except ImportError:
                raise ImportError("Anthropic library not installed. Run: pip install anthropic")
        else:
            raise ValueError("Provider must be 'openai' or 'claude'")
    
    def extract_triples(self, messages: List[Dict], system_prompt: str, user_prompt: str, 
                       template_type: str = "", template_name: str = "",
                       workflow_step: str = "", node_name: str = "") -> Dict[str, Any]:
        """Extract triples using the configured LLM with recording."""
        
        self.request_count += 1
        
        # Use recording context manager
        with record_llm_call(
            messages=messages,
            template_type=template_type,
            template_name=template_name,
            provider=self.provider,
            model_name=self.model,
            workflow_step=workflow_step,
            node_name=node_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=2000,
            segment_id=messages[0].get('segment_id') if messages else None
        ) as record:
            
            try:
                if self.provider == "openai":
                    response = self._call_openai(system_prompt, user_prompt)
                else:  # claude
                    response = self._call_claude(system_prompt, user_prompt)
                
                # Update cost tracking
                if 'usage' in response:
                    usage = response['usage']
                    input_tokens = usage.get('prompt_tokens', 0)
                    output_tokens = usage.get('completion_tokens', 0)
                    
                    cost = (input_tokens * self.input_cost_per_1k / 1000 + 
                           output_tokens * self.output_cost_per_1k / 1000)
                    
                    self.total_cost += cost
                    self.total_tokens += input_tokens + output_tokens
                    
                    # Update recording data
                    if record:
                        record.input_tokens = input_tokens
                        record.output_tokens = output_tokens
                        record.total_tokens = input_tokens + output_tokens
                        record.cost_usd = cost
                        record.raw_response = response.get("content", "")
                        
                        # Try to parse triples
                        try:
                            parsed_triples = json.loads(response.get("content", "[]"))
                            record.parsed_triples = parsed_triples
                        except json.JSONDecodeError:
                            record.parsed_triples = []
                
                return response
                
            except Exception as e:
                # Update record with error info
                if record:
                    record.success = False
                    record.error_message = str(e)
                
                # Return fallback response
                return {"content": "[]", "usage": {"prompt_tokens": 0, "completion_tokens": 0}}
    
    def _call_openai(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        return {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        }
    
    def _call_claude(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call Claude API."""
        response = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.1,
            max_tokens=2000
        )
        
        return {
            "content": response.content[0].text,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens
            }
        }
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost and usage summary."""
        return {
            "total_requests": self.request_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "avg_cost_per_request": round(self.total_cost / max(1, self.request_count), 4),
            "provider": self.provider,
            "model": self.model
        }


class RecordedLLMSegmentProcessor:
    """Enhanced segment processor with recording capabilities."""
    
    def __init__(self, llm_client: RecordedLLMClient, batch_size: int = 20, config_path: str = None):
        self.llm_client = llm_client
        self.batch_size = batch_size
        
        # Import and initialize templates
        try:
            # Try relative imports first (when used as package)
            from .workflow_state import Triple
            from .config import ConfigManager
        except ImportError:
            # Fall back to direct imports (when running as script)
            from workflow_state import Triple
            from config import ConfigManager
        
        self.config_manager = ConfigManager() if config_path is None else ConfigManager()
        self.templates = self.config_manager.prompt_manager
    
    def process_segment(self, segment_messages: List[Dict], segment_id: str) -> List['Triple']:
        """Process a segment of messages using LLM with recording."""
        all_triples = []
        
        # Group messages by type for batch processing
        from collections import defaultdict
        by_type = defaultdict(list)
        for msg in segment_messages:
            by_type[msg['type']].append(msg)
        
        # Process each message type
        for msg_type, messages in by_type.items():
            if not messages:
                continue
            
            # Get the appropriate processing method
            if msg_type == "question":
                triples = self._process_with_recording(
                    messages, "question", "question_extraction", 
                    self.templates.get_question_prompt
                )
            elif msg_type == "strategy":
                triples = self._process_with_recording(
                    messages, "strategy", "strategy_extraction",
                    self.templates.get_strategy_prompt
                )
            elif msg_type == "analysis":
                triples = self._process_with_recording(
                    messages, "analysis", "analysis_extraction",
                    self.templates.get_analysis_prompt
                )
            elif msg_type == "answer":
                triples = self._process_with_recording(
                    messages, "answer", "answer_extraction",
                    self.templates.get_answer_prompt
                )
            else:
                # Handle other types with generic processing
                triples = self._process_generic(messages, msg_type)
            
            all_triples.extend(triples)
        
        return all_triples
    
    def _process_with_recording(self, messages: List[Dict], template_type: str, 
                              workflow_step: str, prompt_func) -> List['Triple']:
        """Process messages with recording enabled."""
        from workflow_state import Triple
        import json
        
        triples = []
        
        # Process in batches
        for i in range(0, len(messages), self.batch_size):
            batch = messages[i:i + self.batch_size]
            
            system_prompt = self.templates.get_system_prompt()
            user_prompt = prompt_func(batch)
            
            response = self.llm_client.extract_triples(
                batch, system_prompt, user_prompt,
                template_type=template_type,
                template_name=f"{template_type}_template",
                workflow_step=workflow_step,
                node_name=f"extract_{template_type}_node"
            )
            
            try:
                extracted = json.loads(response["content"])
                for triple_data in extracted:
                    if len(triple_data) == 3:
                        # Find the corresponding message
                        for msg in batch:
                            if msg['author'] == triple_data[0]:
                                triple = Triple(
                                    subject=triple_data[0],
                                    predicate=triple_data[1],
                                    object=triple_data[2],
                                    message_id=msg['message_id'],
                                    segment_id=msg['segment_id'],
                                    timestamp=msg['timestamp'],
                                    confidence=self.templates.get_confidence_score(template_type)
                                )
                                triples.append(triple)
                                break
            except json.JSONDecodeError:
                pass
        
        return triples
    
    def _process_generic(self, messages: List[Dict], msg_type: str) -> List['Triple']:
        """Generic processing for unrecognized message types."""
        from workflow_state import Triple
        
        triples = []
        for msg in messages:
            content = msg['clean_text'][:60] + '...' if len(msg['clean_text']) > 60 else msg['clean_text']
            
            triple = Triple(
                subject=msg['author'],
                predicate='discusses',
                object=content,
                message_id=msg['message_id'],
                segment_id=msg['segment_id'],
                timestamp=msg['timestamp'],
                confidence=0.6
            )
            triples.append(triple)
        
        return triples