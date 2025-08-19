"""
Step 3: Entity & Relation Extraction Layer - LLM-Powered Version
Implementation using OpenAI GPT and Claude APIs as per README specification

This version uses LLM APIs for high-accuracy extraction with segment-based batching
for optimal cost/quality trade-offs.
"""

import json
import re
import datetime
import os
import time
import yaml
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
import logging
from collections import defaultdict

class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy data types."""
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, (np.integer, np.floating, np.bool_)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
        except ImportError:
            pass
        return super().default(obj)

logger = logging.getLogger(__name__)


@dataclass
class Triple:
    """Knowledge graph triple with metadata according to README spec."""
    subject: str
    predicate: str
    object: str
    message_id: str
    segment_id: str
    timestamp: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # Ensure confidence is JSON serializable
        try:
            import numpy as np
            if isinstance(result['confidence'], (np.float32, np.float64)):
                result['confidence'] = float(result['confidence'])
        except ImportError:
            pass
        return result


class LLMClient:
    """Unified client for OpenAI and Claude APIs with cost tracking."""
    
    def __init__(self, provider: str = "openai", model: str = None):
        self.provider = provider.lower()
        self.total_cost = 0.0
        self.total_tokens = 0
        self.request_count = 0
        
        if self.provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                # Check for model in environment variable first
                self.model = model or os.getenv("OPENAI_MODEL") or "gpt-3.5-turbo"
                # Pricing per 1K tokens (as of 2024)
                self.input_cost_per_1k = 0.0015 if "gpt-3.5" in self.model else 0.01
                self.output_cost_per_1k = 0.002 if "gpt-3.5" in self.model else 0.03
                logger.info(f"Initialized OpenAI client with model: {self.model}")
            except ImportError:
                raise ImportError("OpenAI library not installed. Run: pip install openai")
                
        elif self.provider == "claude":
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                # Check for model in environment variable first
                self.model = model or os.getenv("ANTHROPIC_MODEL") or "claude-3-haiku-20240307"
                # Pricing per 1K tokens for Claude
                self.input_cost_per_1k = 0.00025 if "haiku" in self.model else 0.003
                self.output_cost_per_1k = 0.00125 if "haiku" in self.model else 0.015
                logger.info(f"Initialized Claude client with model: {self.model}")
            except ImportError:
                raise ImportError("Anthropic library not installed. Run: pip install anthropic")
        else:
            raise ValueError("Provider must be 'openai' or 'claude'")
    
    def extract_triples(self, messages: List[Dict], system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Extract triples using the configured LLM."""
        self.request_count += 1
        
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
                
                logger.debug(f"Request {self.request_count}: {input_tokens}+{output_tokens} tokens, ${cost:.4f}")
            
            return response
            
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
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


class PromptTemplates:
    """LLM prompt templates for different message types loaded from YAML configuration."""
    
    def __init__(self, config_path: str = None):
        """Initialize prompt templates from YAML configuration."""
        if config_path is None:
            config_path = Path(__file__).parent / "prompts.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load prompt configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded prompt templates from {self.config_path}")
                return config
        except FileNotFoundError:
            logger.error(f"Prompt configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for LLM extraction."""
        return self.config['system']['content']
    
    def get_question_prompt(self, messages: List[Dict]) -> str:
        """Prompt for extracting question triples."""
        message_text = "\n".join([f"Author: {m['author']}, Text: {m['clean_text']}" for m in messages])
        template = self.config['templates']['question']['instruction']
        return template.format(message_text=message_text)
    
    def get_strategy_prompt(self, messages: List[Dict]) -> str:
        """Prompt for extracting strategy discussion triples."""
        message_text = "\n".join([f"Author: {m['author']}, Text: {m['clean_text']}" for m in messages])
        template = self.config['templates']['strategy']['instruction']
        return template.format(message_text=message_text)
    
    def get_analysis_prompt(self, messages: List[Dict]) -> str:
        """Prompt for extracting analysis triples."""
        message_text = "\n".join([f"Author: {m['author']}, Text: {m['clean_text']}" for m in messages])
        template = self.config['templates']['analysis']['instruction']
        return template.format(message_text=message_text)
    
    def get_answer_prompt(self, messages: List[Dict]) -> str:
        """Prompt for extracting answer/info triples."""
        message_text = "\n".join([f"Author: {m['author']}, Text: {m['clean_text']}" for m in messages])
        template = self.config['templates']['answer']['instruction']
        return template.format(message_text=message_text)
    
    def get_qa_linking_prompt(self, questions: List[Dict], answers: List[Dict]) -> str:
        """Prompt for linking questions to answers."""
        q_text = "\n".join([f"Q{i}: {q['message_id']} - {q['author']}: {q['clean_text']}" 
                           for i, q in enumerate(questions)])
        a_text = "\n".join([f"A{i}: {a['message_id']} - {a['author']}: {a['clean_text']}" 
                           for i, a in enumerate(answers)])
        template = self.config['templates']['qa_linking']['instruction']
        return template.format(q_text=q_text, a_text=a_text)
    
    def get_confidence_score(self, message_type: str) -> float:
        """Get confidence score for a message type from configuration."""
        return self.config.get('config', {}).get('confidence_scores', {}).get(message_type, 0.75)
    
    def get_predicates(self, message_type: str) -> List[str]:
        """Get expected predicates for a message type from configuration."""
        return self.config.get('config', {}).get('predicates', {}).get(message_type, [])


class LLMSegmentProcessor:
    """Processes message segments using LLM APIs with batching for efficiency."""
    
    def __init__(self, llm_client: LLMClient, batch_size: int = 20, config_path: str = None):
        self.llm_client = llm_client
        self.batch_size = batch_size
        self.templates = PromptTemplates(config_path)
        
        # Simple rule-based fallback for some types
        self._init_rule_patterns()
    
    def _init_rule_patterns(self):
        """Initialize rule-based patterns for alert/signal types."""
        self.alert_patterns = [
            r'\b(alert|warning|notice|reminder|announcement)\b',
            r'\b(fomc|fed|cpi|inflation|earnings|report|meeting)\b',
            r'\b(volatility|expected|caution|watch)\b'
        ]
        
        self.performance_pattern = re.compile(r'([+-]?\d+(?:\.\d+)?)\s*%')
        self.return_keywords = re.compile(r'\b(profit|loss|gain|return|made|lost|performance)\b', re.IGNORECASE)
    
    def process_segment(self, segment_messages: List[Dict], segment_id: str) -> List[Triple]:
        """Process a segment of messages using appropriate LLM strategies."""
        all_triples = []
        
        # Group messages by type for batch processing
        by_type = defaultdict(list)
        for msg in segment_messages:
            by_type[msg['type']].append(msg)
        
        logger.debug(f"Processing segment {segment_id} with {len(segment_messages)} messages")
        
        # Process each message type
        for msg_type, messages in by_type.items():
            if not messages:
                continue
                
            logger.debug(f"  Processing {len(messages)} {msg_type} messages")
            
            if msg_type == "question":
                triples = self._process_questions(messages)
            elif msg_type == "strategy":
                triples = self._process_strategies(messages)
            elif msg_type == "analysis":
                triples = self._process_analysis(messages)
            elif msg_type == "answer":
                triples = self._process_answers(messages)
            elif msg_type == "alert":
                triples = self._process_alerts_rule_based(messages)  # Keep rule-based for alerts
            elif msg_type == "performance":
                triples = self._process_performance_rule_based(messages)  # Keep rule-based for performance
            else:
                # Fallback: treat as general discussion
                triples = self._process_discussion(messages)
            
            all_triples.extend(triples)
        
        # LLM-based Q&A linking for the segment
        questions = [msg for msg in segment_messages if msg['type'] == 'question']
        answers = [msg for msg in segment_messages if msg['type'] == 'answer']
        
        if questions and answers:
            qa_triples = self._link_qa_with_llm(questions, answers, segment_id)
            all_triples.extend(qa_triples)
        
        return all_triples
    
    def _process_questions(self, messages: List[Dict]) -> List[Triple]:
        """Process question messages using LLM."""
        triples = []
        
        # Process in batches
        for i in range(0, len(messages), self.batch_size):
            batch = messages[i:i + self.batch_size]
            
            system_prompt = self.templates.get_system_prompt()
            user_prompt = self.templates.get_question_prompt(batch)
            
            response = self.llm_client.extract_triples(batch, system_prompt, user_prompt)
            
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
                                    confidence=self.templates.get_confidence_score('question')
                                )
                                triples.append(triple)
                                break
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response for questions: {response['content'][:100]}")
                
        return triples
    
    def _process_strategies(self, messages: List[Dict]) -> List[Triple]:
        """Process strategy messages using LLM."""
        triples = []
        
        for i in range(0, len(messages), self.batch_size):
            batch = messages[i:i + self.batch_size]
            
            system_prompt = self.templates.get_system_prompt()
            user_prompt = self.templates.get_strategy_prompt(batch)
            
            response = self.llm_client.extract_triples(batch, system_prompt, user_prompt)
            
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
                                    confidence=self.templates.get_confidence_score('strategy')
                                )
                                triples.append(triple)
                                break
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response for strategies: {response['content'][:100]}")
                
        return triples
    
    def _process_analysis(self, messages: List[Dict]) -> List[Triple]:
        """Process analysis messages using LLM (best for abstract reasoning)."""
        triples = []
        
        for i in range(0, len(messages), self.batch_size):
            batch = messages[i:i + self.batch_size]
            
            system_prompt = self.templates.get_system_prompt()
            user_prompt = self.templates.get_analysis_prompt(batch)
            
            response = self.llm_client.extract_triples(batch, system_prompt, user_prompt)
            
            try:
                extracted = json.loads(response["content"])
                for triple_data in extracted:
                    if len(triple_data) == 3:
                        for msg in batch:
                            if msg['author'] == triple_data[0]:
                                triple = Triple(
                                    subject=triple_data[0],
                                    predicate=triple_data[1],
                                    object=triple_data[2],
                                    message_id=msg['message_id'],
                                    segment_id=msg['segment_id'],
                                    timestamp=msg['timestamp'],
                                    confidence=self.templates.get_confidence_score('analysis')
                                )
                                triples.append(triple)
                                break
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response for analysis: {response['content'][:100]}")
                
        return triples
    
    def _process_answers(self, messages: List[Dict]) -> List[Triple]:
        """Process answer messages using LLM."""
        triples = []
        
        for i in range(0, len(messages), self.batch_size):
            batch = messages[i:i + self.batch_size]
            
            system_prompt = self.templates.get_system_prompt()
            user_prompt = self.templates.get_answer_prompt(batch)
            
            response = self.llm_client.extract_triples(batch, system_prompt, user_prompt)
            
            try:
                extracted = json.loads(response["content"])
                for triple_data in extracted:
                    if len(triple_data) == 3:
                        for msg in batch:
                            if msg['author'] == triple_data[0]:
                                triple = Triple(
                                    subject=triple_data[0],
                                    predicate=triple_data[1],
                                    object=triple_data[2],
                                    message_id=msg['message_id'],
                                    segment_id=msg['segment_id'],
                                    timestamp=msg['timestamp'],
                                    confidence=self.templates.get_confidence_score('answer')
                                )
                                triples.append(triple)
                                break
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response for answers: {response['content'][:100]}")
                
        return triples
    
    def _process_discussion(self, messages: List[Dict]) -> List[Triple]:
        """Process general discussion messages."""
        triples = []
        
        for msg in messages:
            # Simple extraction for discussion
            content = msg['clean_text'][:60] + '...' if len(msg['clean_text']) > 60 else msg['clean_text']
            
            triple = Triple(
                subject=msg['author'],
                predicate='discusses',
                object=content,
                message_id=msg['message_id'],
                segment_id=msg['segment_id'],
                timestamp=msg['timestamp'],
                confidence=self.templates.get_confidence_score('discussion')
            )
            triples.append(triple)
            
        return triples
    
    def _process_alerts_rule_based(self, messages: List[Dict]) -> List[Triple]:
        """Process alerts using rule-based approach (more reliable for alerts)."""
        triples = []
        
        for msg in messages:
            content = msg['clean_text']
            is_alert = any(re.search(pattern, content, re.IGNORECASE) for pattern in self.alert_patterns)
            
            if is_alert or msg['type'] == 'alert':
                alert_content = content[:60] + '...' if len(content) > 60 else content
                
                triple = Triple(
                    subject=msg['author'],
                    predicate='alerts',
                    object=f"all_members about {alert_content}",
                    message_id=msg['message_id'],
                    segment_id=msg['segment_id'],
                    timestamp=msg['timestamp'],
                    confidence=self.templates.get_confidence_score('alert')
                )
                triples.append(triple)
                
        return triples
    
    def _process_performance_rule_based(self, messages: List[Dict]) -> List[Triple]:
        """Process performance using rule-based approach (reliable for % patterns)."""
        triples = []
        
        for msg in messages:
            content = msg['clean_text']
            percentages = self.performance_pattern.findall(content)
            
            if percentages and self.return_keywords.search(content):
                for pct in percentages:
                    performance_desc = f"+{pct}% return" if not pct.startswith('-') else f"{pct}% loss"
                    
                    triple = Triple(
                        subject=msg['author'],
                        predicate='reports_return',
                        object=performance_desc,
                        message_id=msg['message_id'],
                        segment_id=msg['segment_id'],
                        timestamp=msg['timestamp'],
                        confidence=self.templates.get_confidence_score('performance')
                    )
                    triples.append(triple)
                    
        return triples
    
    def _link_qa_with_llm(self, questions: List[Dict], answers: List[Dict], segment_id: str) -> List[Triple]:
        """Link Q&A pairs using LLM reasoning."""
        if not questions or not answers:
            return []
        
        triples = []
        
        # Process Q&A linking with smaller batches (more expensive)
        max_qa_batch = 5  # Smaller batches for Q&A linking
        
        for i in range(0, len(questions), max_qa_batch):
            q_batch = questions[i:i + max_qa_batch]
            
            system_prompt = self.templates.get_system_prompt()
            user_prompt = self.templates.get_qa_linking_prompt(q_batch, answers)
            
            response = self.llm_client.extract_triples(q_batch + answers, system_prompt, user_prompt)
            
            try:
                extracted = json.loads(response["content"])
                for triple_data in extracted:
                    if len(triple_data) == 3 and triple_data[1] == "answered_by":
                        triple = Triple(
                            subject=triple_data[0],
                            predicate=triple_data[1],
                            object=triple_data[2],
                            message_id=f"{triple_data[0]}_llm_link_{triple_data[2]}",
                            segment_id=segment_id,
                            timestamp=datetime.datetime.now().isoformat(),
                            confidence=self.templates.get_confidence_score('qa_linking')
                        )
                        triples.append(triple)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response for Q&A linking: {response['content'][:100]}")
        
        return triples


class LLMTripleExtractor:
    """Main LLM-powered extraction coordinator."""
    
    def __init__(self, provider: str = "openai", model: str = None, batch_size: int = 20, config_path: str = None):
        """
        Initialize LLM extractor.
        
        Args:
            provider: "openai" or "claude"  
            model: Specific model name (defaults to gpt-3.5-turbo or claude-3-haiku)
            batch_size: Messages per LLM request (10-20 for accuracy, 50-100 for efficiency)
            config_path: Path to YAML prompt configuration file
        """
        self.llm_client = LLMClient(provider, model)
        self.processor = LLMSegmentProcessor(self.llm_client, batch_size, config_path)
        
        logger.info(f"Initialized LLM extractor: {provider} with batch_size={batch_size}")
        if config_path:
            logger.info(f"Using custom prompt config: {config_path}")
    
    def extract_triples(self, messages: List[Dict[str, Any]]) -> List[Triple]:
        """Extract triples using LLM APIs with segment-based processing."""
        logger.info(f"Starting LLM-based extraction on {len(messages)} messages")
        
        # Group messages by segment for context-aware processing
        segments = defaultdict(list)
        for msg in messages:
            segments[msg['segment_id']].append(msg)
        
        logger.info(f"Processing {len(segments)} segments with LLM")
        
        all_triples = []
        processed_segments = 0
        
        for segment_id, segment_messages in segments.items():
            processed_segments += 1
            
            if processed_segments % 10 == 0:
                logger.info(f"Processed {processed_segments}/{len(segments)} segments")
                cost_summary = self.llm_client.get_cost_summary()
                logger.info(f"Current cost: ${cost_summary['total_cost_usd']}")
            
            # Sort messages by timestamp for context
            segment_messages.sort(key=lambda x: x['timestamp'])
            
            # Process segment with LLM
            segment_triples = self.processor.process_segment(segment_messages, segment_id)
            all_triples.extend(segment_triples)
            
            # Rate limiting (be nice to APIs)
            time.sleep(0.1)
        
        # Final cost summary
        cost_summary = self.llm_client.get_cost_summary()
        logger.info(f"LLM extraction complete!")
        logger.info(f"Total: {len(all_triples)} triples from {len(messages)} messages")
        logger.info(f"Cost: ${cost_summary['total_cost_usd']} ({cost_summary['total_requests']} requests)")
        
        return all_triples
    
    def process_file(self, input_file: str, output_file: str) -> int:
        """Process a JSONL file and extract triples using LLM."""
        # Read messages
        messages = []
        with open(input_file, 'r') as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
        
        logger.info(f"Loaded {len(messages)} messages from {input_file}")
        
        # Extract triples
        triples = self.extract_triples(messages)
        
        # Write output
        with open(output_file, 'w') as f:
            for triple in triples:
                f.write(json.dumps(triple.to_dict(), cls=NumpyEncoder) + '\n')
        
        # Write cost summary
        cost_summary = self.llm_client.get_cost_summary()
        cost_file = output_file.replace('.jsonl', '_cost_summary.json')
        with open(cost_file, 'w') as f:
            json.dump(cost_summary, f, indent=2)
        
        logger.info(f"Wrote {len(triples)} triples to {output_file}")
        logger.info(f"Cost summary saved to {cost_file}")
        
        return len(triples)
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost and usage summary."""
        return self.llm_client.get_cost_summary()


if __name__ == "__main__":
    import sys
    import argparse
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(description='LLM-powered triple extraction')
    parser.add_argument('input_file', help='Input JSONL file with classified messages')
    parser.add_argument('output_file', help='Output JSONL file for extracted triples')
    parser.add_argument('--provider', choices=['openai', 'claude'], default='openai', 
                       help='LLM provider (default: openai)')
    parser.add_argument('--model', help='Specific model name')
    parser.add_argument('--batch-size', type=int, default=20, 
                       help='Messages per LLM request (default: 20)')
    parser.add_argument('--config', help='Path to YAML prompt configuration file')
    
    args = parser.parse_args()
    
    # Check for API keys
    if args.provider == 'openai' and not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    elif args.provider == 'claude' and not os.getenv('ANTHROPIC_API_KEY'):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)
    
    # Initialize extractor
    extractor = LLMTripleExtractor(
        provider=args.provider,
        model=args.model,
        batch_size=args.batch_size,
        config_path=args.config
    )
    
    print(f"LLM Step 3 Processing: {args.input_file} -> {args.output_file}")
    print(f"Provider: {args.provider}, Batch size: {args.batch_size}")
    
    # Process file
    num_triples = extractor.process_file(args.input_file, args.output_file)
    
    # Final summary
    cost_summary = extractor.get_cost_summary()
    print(f"\n✓ Extracted {num_triples} triples")
    print(f"✓ Total cost: ${cost_summary['total_cost_usd']}")
    print(f"✓ Requests: {cost_summary['total_requests']}")
    print(f"✓ Results saved to: {args.output_file}")