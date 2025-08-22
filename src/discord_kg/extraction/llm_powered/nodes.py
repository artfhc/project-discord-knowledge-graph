"""
LangGraph workflow nodes for Discord Knowledge Graph extraction.

This module contains all the individual processing nodes that make up
the extraction workflow, each with a single responsibility.
"""

import json
import logging
import time
import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
import re

try:
    # Try relative imports first (when used as package)
    from .workflow_state import (
        WorkflowState, NodeResult, ProcessingStatus, ProcessingMetrics, 
        Triple, MessageType, update_state_metrics, log_error,
        get_messages_by_type, has_questions_and_answers
    )
    from .config import ConfigManager
    from .llm_providers import LLMProviderFactory, TripleExtractor
except ImportError:
    # Fall back to direct imports (when running as script)
    from workflow_state import (
        WorkflowState, NodeResult, ProcessingStatus, ProcessingMetrics, 
        Triple, MessageType, update_state_metrics, log_error,
        get_messages_by_type, has_questions_and_answers
    )
    from config import ConfigManager
    from llm_providers import LLMProviderFactory, TripleExtractor

logger = logging.getLogger(__name__)


def preprocessing_node(state: WorkflowState) -> WorkflowState:
    """
    Preprocessing node: Clean and validate messages, group by segments.
    
    This node handles:
    - Message validation and cleaning
    - Segment grouping for context-aware processing
    - Initial data structure preparation
    """
    start_time = time.time()
    state["current_step"] = "preprocessing"
    
    try:
        logger.info(f"Starting preprocessing of {len(state['raw_messages'])} messages")
        
        processed_messages = []
        segments = defaultdict(list)
        error_count = 0
        
        for msg in state["raw_messages"]:
            try:
                # Validate required fields
                required_fields = ['message_id', 'author', 'timestamp']
                if not all(field in msg for field in required_fields):
                    logger.warning(f"Message {msg.get('message_id', 'unknown')} missing required fields")
                    error_count += 1
                    continue
                
                # Ensure clean_text exists
                if 'clean_text' not in msg:
                    msg['clean_text'] = msg.get('text', '').strip()
                
                # Ensure segment_id exists
                if 'segment_id' not in msg:
                    # Generate segment_id based on timestamp or use default
                    msg['segment_id'] = state.get("segment_id", "default_segment")
                
                # Basic text cleaning
                if msg['clean_text']:
                    # Remove excessive whitespace
                    msg['clean_text'] = re.sub(r'\s+', ' ', msg['clean_text']).strip()
                    
                    # Skip very short messages (likely noise)
                    if len(msg['clean_text']) < 5:
                        continue
                
                processed_messages.append(msg)
                segments[msg['segment_id']].append(msg)
                
            except Exception as e:
                logger.warning(f"Error processing message {msg.get('message_id', 'unknown')}: {e}")
                error_count += 1
        
        # Update state
        state["processed_messages"] = processed_messages
        state["message_segments"] = dict(segments)
        
        # Create result
        processing_time = int((time.time() - start_time) * 1000)
        metrics = ProcessingMetrics(
            messages_processed=len(processed_messages),
            processing_time_ms=processing_time,
            error_count=error_count
        )
        
        result = NodeResult(
            status=ProcessingStatus.COMPLETED,
            data={
                "processed_count": len(processed_messages),
                "segment_count": len(segments),
                "error_count": error_count
            },
            metrics=metrics
        )
        
        state["preprocessing_result"] = result
        update_state_metrics(state, result)
        
        logger.info(f"Preprocessing completed: {len(processed_messages)} messages in {len(segments)} segments")
        return state
        
    except Exception as e:
        error_msg = f"Preprocessing failed: {str(e)}"
        log_error(state, error_msg, "preprocessing")
        
        processing_time = int((time.time() - start_time) * 1000)
        result = NodeResult(
            status=ProcessingStatus.FAILED,
            error=error_msg,
            metrics=ProcessingMetrics(processing_time_ms=processing_time, error_count=1)
        )
        
        state["preprocessing_result"] = result
        update_state_metrics(state, result)
        
        return state


def classification_node(state: WorkflowState) -> WorkflowState:
    """
    Classification node: Classify messages by type using rule-based approach.
    
    This is kept as rule-based for efficiency, as the original system
    had reliable classification patterns.
    """
    start_time = time.time()
    state["current_step"] = "classification"
    
    try:
        messages = state["processed_messages"]
        logger.info(f"Starting classification of {len(messages)} messages")
        
        classified_messages = defaultdict(list)
        
        # Classification patterns (from original system)
        question_patterns = [
            r'\b(what|how|why|when|where|which|who|can|could|should|would|is|are|will)\b.*\?',
            r'\b(help|advice|suggestions?|recommendations?|thoughts?|opinions?)\b',
            r'\b(anyone|anybody)\s+(know|tried|using)\b'
        ]
        
        strategy_patterns = [
            r'\b(strategy|approach|plan|setup|position|trade)\b',
            r'\b(buy|sell|long|short|calls?|puts?|spread)\b',
            r'\b(bullish|bearish|neutral|momentum)\b'
        ]
        
        analysis_patterns = [
            r'\b(analysis|outlook|forecast|prediction|expect)\b',
            r'\b(support|resistance|trend|pattern|chart)\b',
            r'\b(technical|fundamental|sentiment)\b'
        ]
        
        alert_patterns = [
            r'\b(alert|warning|notice|announcement)\b',
            r'\b(fomc|fed|cpi|inflation|earnings|meeting)\b',
            r'\b(volatility|expected|caution|watch)\b'
        ]
        
        performance_pattern = re.compile(r'([+-]?\d+(?:\.\d+)?)\s*%')
        return_keywords = re.compile(r'\b(profit|loss|gain|return|made|lost|performance)\b', re.IGNORECASE)
        
        for msg in messages:
            text = msg['clean_text'].lower()
            
            # Check for performance first (most specific)
            if performance_pattern.search(text) and return_keywords.search(text):
                msg['type'] = MessageType.PERFORMANCE.value
            
            # Check for alerts
            elif any(re.search(pattern, text, re.IGNORECASE) for pattern in alert_patterns):
                msg['type'] = MessageType.ALERT.value
            
            # Check for questions
            elif any(re.search(pattern, text, re.IGNORECASE) for pattern in question_patterns):
                msg['type'] = MessageType.QUESTION.value
            
            # Check for strategy
            elif any(re.search(pattern, text, re.IGNORECASE) for pattern in strategy_patterns):
                msg['type'] = MessageType.STRATEGY.value
            
            # Check for analysis
            elif any(re.search(pattern, text, re.IGNORECASE) for pattern in analysis_patterns):
                msg['type'] = MessageType.ANALYSIS.value
            
            # Default to discussion, but check if it might be an answer
            else:
                # Simple heuristic: longer messages following questions might be answers
                if len(text) > 50 and not text.endswith('?'):
                    msg['type'] = MessageType.ANSWER.value
                else:
                    msg['type'] = MessageType.DISCUSSION.value
            
            classified_messages[msg['type']].append(msg)
        
        # Update state
        state["classified_messages"] = dict(classified_messages)
        
        # Create result with classification summary
        classification_summary = {msg_type: len(msgs) for msg_type, msgs in classified_messages.items()}
        
        processing_time = int((time.time() - start_time) * 1000)
        metrics = ProcessingMetrics(
            messages_processed=len(messages),
            processing_time_ms=processing_time
        )
        
        result = NodeResult(
            status=ProcessingStatus.COMPLETED,
            data=classification_summary,
            metrics=metrics
        )
        
        state["classification_result"] = result
        update_state_metrics(state, result)
        
        logger.info(f"Classification completed: {classification_summary}")
        return state
        
    except Exception as e:
        error_msg = f"Classification failed: {str(e)}"
        log_error(state, error_msg, "classification")
        
        processing_time = int((time.time() - start_time) * 1000)
        result = NodeResult(
            status=ProcessingStatus.FAILED,
            error=error_msg,
            metrics=ProcessingMetrics(processing_time_ms=processing_time, error_count=1)
        )
        
        state["classification_result"] = result
        update_state_metrics(state, result)
        
        return state


def extraction_node_factory(message_type: str):
    """Factory function to create extraction nodes for specific message types."""
    
    def extraction_node(state: WorkflowState) -> WorkflowState:
        """Extract triples for a specific message type using LLM."""
        start_time = time.time()
        step_name = f"extraction_{message_type}"
        state["current_step"] = step_name
        
        try:
            # Get messages of this type
            messages = get_messages_by_type(state, message_type)
            
            if not messages:
                logger.info(f"No {message_type} messages to process")
                result = NodeResult(
                    status=ProcessingStatus.SKIPPED,
                    data={"message_count": 0, "triples_extracted": 0}
                )
                state["extraction_results"][message_type] = result
                return state
            
            logger.info(f"Starting {message_type} extraction for {len(messages)} messages")
            
            # Initialize configuration and LLM
            config_manager = ConfigManager(state.get("config_path"))
            provider = LLMProviderFactory.create_from_string(
                state["llm_provider"], 
                state.get("llm_model")
            )
            extractor = TripleExtractor(provider)
            
            # Get prompts
            system_prompt = config_manager.get_system_prompt()
            template = config_manager.get_template(message_type)
            confidence_score = config_manager.get_confidence_score(message_type)
            
            # Process in batches
            batch_size = state["batch_size"]
            all_triples = []
            
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]
                
                # Extract triples for this batch
                extracted = extractor.extract_from_messages(
                    batch, system_prompt, template.instruction
                )
                
                # Convert to Triple objects
                for triple_data in extracted:
                    if len(triple_data) >= 3:
                        # Find corresponding message (simple matching by author)
                        for msg in batch:
                            if msg['author'] == triple_data[0]:
                                triple = Triple(
                                    subject=str(triple_data[0]),
                                    predicate=str(triple_data[1]),
                                    object=str(triple_data[2]),
                                    message_id=msg['message_id'],
                                    segment_id=msg['segment_id'],
                                    timestamp=msg['timestamp'],
                                    confidence=confidence_score,
                                    extraction_method="llm"
                                )
                                all_triples.append(triple)
                                break
                
                # Rate limiting
                time.sleep(state.get("rate_limit_delay_ms", 100) / 1000.0)
            
            # Add to state results
            state["extracted_triples"].extend(all_triples)
            
            # Create result
            processing_time = int((time.time() - start_time) * 1000)
            provider_metrics = provider.get_metrics()
            
            metrics = ProcessingMetrics(
                messages_processed=len(messages),
                triples_extracted=len(all_triples),
                api_calls=provider_metrics.api_calls,
                total_tokens=provider_metrics.total_tokens,
                total_cost=provider_metrics.total_cost,
                processing_time_ms=processing_time
            )
            
            result = NodeResult(
                status=ProcessingStatus.COMPLETED,
                data={
                    "message_count": len(messages),
                    "triples_extracted": len(all_triples),
                    "batches_processed": (len(messages) + batch_size - 1) // batch_size
                },
                metrics=metrics
            )
            
            state["extraction_results"][message_type] = result
            update_state_metrics(state, result)
            
            logger.info(f"{message_type.capitalize()} extraction completed: {len(all_triples)} triples from {len(messages)} messages")
            return state
            
        except Exception as e:
            error_msg = f"{message_type.capitalize()} extraction failed: {str(e)}"
            log_error(state, error_msg, step_name)
            
            processing_time = int((time.time() - start_time) * 1000)
            result = NodeResult(
                status=ProcessingStatus.FAILED,
                error=error_msg,
                metrics=ProcessingMetrics(processing_time_ms=processing_time, error_count=1)
            )
            
            state["extraction_results"][message_type] = result
            update_state_metrics(state, result)
            
            return state
    
    # Set function name for better debugging
    extraction_node.__name__ = f"extract_{message_type}_node"
    return extraction_node


def qa_linking_node(state: WorkflowState) -> WorkflowState:
    """Link questions to answers using LLM-based semantic matching."""
    start_time = time.time()
    state["current_step"] = "qa_linking"
    
    try:
        # Check if Q&A linking should be skipped
        if state.get("should_skip_qa_linking") or not has_questions_and_answers(state):
            logger.info("Skipping Q&A linking - no questions or answers found")
            result = NodeResult(
                status=ProcessingStatus.SKIPPED,
                data={"qa_links_created": 0}
            )
            state["qa_linking_result"] = result
            return state
        
        questions = get_messages_by_type(state, MessageType.QUESTION)
        answers = get_messages_by_type(state, MessageType.ANSWER)
        
        logger.info(f"Starting Q&A linking: {len(questions)} questions, {len(answers)} answers")
        
        # Initialize configuration and LLM
        config_manager = ConfigManager(state.get("config_path"))
        provider = LLMProviderFactory.create_from_string(
            state["llm_provider"], 
            state.get("llm_model")
        )
        extractor = TripleExtractor(provider)
        
        # Get prompts
        system_prompt = config_manager.get_system_prompt()
        template = config_manager.get_template("qa_linking")
        confidence_score = config_manager.get_confidence_score("qa_linking")
        
        # Process in smaller batches (Q&A linking is more expensive)
        max_qa_batch = min(5, len(questions))
        qa_links = []
        
        for i in range(0, len(questions), max_qa_batch):
            q_batch = questions[i:i + max_qa_batch]
            
            # Extract Q&A links
            extracted_links = extractor.extract_qa_links(
                q_batch, answers, system_prompt, template.instruction
            )
            
            # Convert to Triple objects
            for link_data in extracted_links:
                if len(link_data) == 3 and link_data[1] == "answered_by":
                    triple = Triple(
                        subject=str(link_data[0]),
                        predicate=str(link_data[1]),
                        object=str(link_data[2]),
                        message_id=f"{link_data[0]}_link_{link_data[2]}",
                        segment_id=state.get("segment_id", "qa_links"),
                        timestamp=datetime.datetime.now().isoformat(),
                        confidence=confidence_score,
                        extraction_method="llm_qa_linking"
                    )
                    qa_links.append(triple)
            
            # Rate limiting
            time.sleep(state.get("rate_limit_delay_ms", 100) / 1000.0)
        
        # Add to state
        state["qa_links"] = qa_links
        
        # Create result
        processing_time = int((time.time() - start_time) * 1000)
        provider_metrics = provider.get_metrics()
        
        metrics = ProcessingMetrics(
            messages_processed=len(questions) + len(answers),
            triples_extracted=len(qa_links),
            api_calls=provider_metrics.api_calls,
            total_tokens=provider_metrics.total_tokens,
            total_cost=provider_metrics.total_cost,
            processing_time_ms=processing_time
        )
        
        result = NodeResult(
            status=ProcessingStatus.COMPLETED,
            data={"qa_links_created": len(qa_links)},
            metrics=metrics
        )
        
        state["qa_linking_result"] = result
        update_state_metrics(state, result)
        
        logger.info(f"Q&A linking completed: {len(qa_links)} links created")
        return state
        
    except Exception as e:
        error_msg = f"Q&A linking failed: {str(e)}"
        log_error(state, error_msg, "qa_linking")
        
        processing_time = int((time.time() - start_time) * 1000)
        result = NodeResult(
            status=ProcessingStatus.FAILED,
            error=error_msg,
            metrics=ProcessingMetrics(processing_time_ms=processing_time, error_count=1)
        )
        
        state["qa_linking_result"] = result
        update_state_metrics(state, result)
        
        return state


def aggregation_node(state: WorkflowState) -> WorkflowState:
    """Aggregate and validate all extracted triples."""
    start_time = time.time()
    state["current_step"] = "aggregation"
    
    try:
        logger.info("Starting result aggregation and validation")
        
        # Collect all triples
        all_triples = []
        all_triples.extend(state["extracted_triples"])
        all_triples.extend(state["qa_links"])
        
        # Deduplication based on content similarity
        deduplicated_triples = []
        seen_triples = set()
        
        for triple in all_triples:
            # Create a normalized key for deduplication
            key = f"{triple.subject}|{triple.predicate}|{triple.object}".lower().strip()
            
            if key not in seen_triples:
                seen_triples.add(key)
                deduplicated_triples.append(triple)
        
        # Basic validation
        validated_triples = []
        validation_errors = 0
        
        for triple in deduplicated_triples:
            try:
                # Check for required fields
                if not all([triple.subject, triple.predicate, triple.object]):
                    validation_errors += 1
                    continue
                
                # Check confidence score is valid
                if not 0.0 <= triple.confidence <= 1.0:
                    triple.confidence = 0.5  # Default fallback
                
                # Ensure all fields are strings
                triple.subject = str(triple.subject).strip()
                triple.predicate = str(triple.predicate).strip()
                triple.object = str(triple.object).strip()
                
                # Skip very short or empty content
                if len(triple.object) < 2:
                    validation_errors += 1
                    continue
                
                validated_triples.append(triple)
                
            except Exception as e:
                logger.warning(f"Error validating triple: {e}")
                validation_errors += 1
        
        # Update state
        state["aggregated_results"] = validated_triples
        
        # Create result
        processing_time = int((time.time() - start_time) * 1000)
        metrics = ProcessingMetrics(
            triples_extracted=len(validated_triples),
            processing_time_ms=processing_time,
            error_count=validation_errors
        )
        
        result = NodeResult(
            status=ProcessingStatus.COMPLETED,
            data={
                "total_triples": len(all_triples),
                "deduplicated_triples": len(deduplicated_triples),
                "validated_triples": len(validated_triples),
                "validation_errors": validation_errors
            },
            metrics=metrics
        )
        
        state["aggregation_result"] = result
        update_state_metrics(state, result)
        
        logger.info(f"Aggregation completed: {len(validated_triples)} final triples (removed {len(all_triples) - len(validated_triples)} duplicates/invalid)")
        return state
        
    except Exception as e:
        error_msg = f"Aggregation failed: {str(e)}"
        log_error(state, error_msg, "aggregation")
        
        processing_time = int((time.time() - start_time) * 1000)
        result = NodeResult(
            status=ProcessingStatus.FAILED,
            error=error_msg,
            metrics=ProcessingMetrics(processing_time_ms=processing_time, error_count=1)
        )
        
        state["aggregation_result"] = result
        update_state_metrics(state, result)
        
        return state


def cost_tracking_node(state: WorkflowState) -> WorkflowState:
    """Generate final cost summary and analytics."""
    start_time = time.time()
    state["current_step"] = "cost_tracking"
    
    try:
        logger.info("Generating cost summary and analytics")
        
        # Aggregate all metrics
        overall_metrics = state["overall_metrics"]
        
        # Create detailed cost summary
        cost_summary = {
            "total_messages_processed": overall_metrics.messages_processed,
            "total_triples_extracted": overall_metrics.triples_extracted,
            "total_api_calls": overall_metrics.api_calls,
            "total_tokens": overall_metrics.total_tokens,
            "total_cost_usd": round(overall_metrics.total_cost, 4),
            "total_processing_time_ms": overall_metrics.processing_time_ms,
            "total_errors": overall_metrics.error_count,
            
            # Efficiency metrics
            "cost_per_message": round(overall_metrics.total_cost / max(1, overall_metrics.messages_processed), 6),
            "cost_per_triple": round(overall_metrics.total_cost / max(1, overall_metrics.triples_extracted), 4),
            "tokens_per_message": round(overall_metrics.total_tokens / max(1, overall_metrics.messages_processed), 2),
            "triples_per_message": round(overall_metrics.triples_extracted / max(1, overall_metrics.messages_processed), 2),
            
            # Configuration
            "llm_provider": state["llm_provider"],
            "llm_model": state.get("llm_model"),
            "batch_size": state["batch_size"],
            
            # Processing breakdown
            "extraction_results": {
                msg_type: {
                    "status": result.status.value,
                    "triples": result.data.get("triples_extracted", 0) if result.data else 0,
                    "cost": result.metrics.total_cost,
                    "api_calls": result.metrics.api_calls
                }
                for msg_type, result in state["extraction_results"].items()
            },
            
            "qa_linking": {
                "status": state["qa_linking_result"].status.value if state["qa_linking_result"] else "skipped",
                "links_created": len(state["qa_links"]),
                "cost": state["qa_linking_result"].metrics.total_cost if state["qa_linking_result"] else 0
            },
            
            # Error summary
            "errors": state["error_log"],
            
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        state["cost_summary"] = cost_summary
        
        # Create result
        processing_time = int((time.time() - start_time) * 1000)
        metrics = ProcessingMetrics(processing_time_ms=processing_time)
        
        result = NodeResult(
            status=ProcessingStatus.COMPLETED,
            data=cost_summary,
            metrics=metrics
        )
        
        update_state_metrics(state, result)
        
        logger.info(f"Cost tracking completed - Total: ${cost_summary['total_cost_usd']} for {cost_summary['total_triples_extracted']} triples")
        return state
        
    except Exception as e:
        error_msg = f"Cost tracking failed: {str(e)}"
        log_error(state, error_msg, "cost_tracking")
        
        # Still create a basic cost summary
        state["cost_summary"] = {
            "error": error_msg,
            "total_cost_usd": state["overall_metrics"].total_cost,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        return state


# Create specific extraction nodes for each message type
extract_question_node = extraction_node_factory("question")
extract_strategy_node = extraction_node_factory("strategy")  
extract_analysis_node = extraction_node_factory("analysis")
extract_answer_node = extraction_node_factory("answer")
extract_alert_node = extraction_node_factory("alert")
extract_performance_node = extraction_node_factory("performance")
extract_discussion_node = extraction_node_factory("discussion")