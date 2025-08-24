"""
Token estimation utilities for managing API rate limits.

Provides approximate token counting and batch size adjustment to stay within
rate limits for different LLM providers.
"""

import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class TokenLimits:
    """Rate limit configuration for different providers."""
    max_tokens_per_minute: int
    max_requests_per_minute: int
    safety_margin: float = 0.8  # Use 80% of limit for safety
    
    @property
    def safe_tokens_per_minute(self) -> int:
        return int(self.max_tokens_per_minute * self.safety_margin)


# Provider-specific rate limits
RATE_LIMITS = {
    "openai": TokenLimits(
        max_tokens_per_minute=90_000,  # GPT-4 tier 1
        max_requests_per_minute=500
    ),
    "claude": TokenLimits(
        max_tokens_per_minute=50_000,  # Claude tier 1
        max_requests_per_minute=50
    )
}


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text using a simple heuristic.
    
    This is an approximation since exact tokenization requires the specific
    model's tokenizer, but it's good enough for rate limit management.
    
    Args:
        text: Input text to estimate tokens for
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    # Basic token estimation:
    # - ~4 characters per token on average for English
    # - Add extra for punctuation and special characters
    # - Account for special tokens like system prompts
    
    char_count = len(text)
    
    # Count words (more accurate than pure character count)
    word_count = len(text.split())
    
    # Estimate based on character count with adjustments
    char_based_estimate = char_count / 3.5  # Slightly conservative
    
    # Estimate based on word count 
    word_based_estimate = word_count * 1.3  # Account for subword tokens
    
    # Use the higher estimate for safety
    estimated_tokens = max(char_based_estimate, word_based_estimate)
    
    # Add overhead for JSON structure, special tokens, etc.
    overhead = estimated_tokens * 0.1
    
    return int(estimated_tokens + overhead)


def estimate_prompt_tokens(system_prompt: str, user_prompt: str) -> int:
    """
    Estimate total tokens for a complete prompt.
    
    Args:
        system_prompt: System prompt text
        user_prompt: User prompt text
        
    Returns:
        Estimated total input tokens
    """
    system_tokens = estimate_tokens(system_prompt)
    user_tokens = estimate_tokens(user_prompt)
    
    # Add overhead for chat format structure
    format_overhead = 10
    
    return system_tokens + user_tokens + format_overhead


def estimate_message_batch_tokens(messages: List[Dict[str, Any]], 
                                system_prompt: str,
                                user_prompt_template: str) -> int:
    """
    Estimate tokens for processing a batch of messages.
    
    Args:
        messages: List of messages to process
        system_prompt: System prompt template
        user_prompt_template: User prompt template with {message_text} placeholder
        
    Returns:
        Estimated total input tokens for the batch
    """
    # Format messages into text
    message_text = "\n".join([
        f"Author: {msg['author']}, Text: {msg.get('clean_text', msg.get('content', ''))}"
        for msg in messages
    ])
    
    # Create the actual user prompt
    user_prompt = user_prompt_template.format(message_text=message_text)
    
    return estimate_prompt_tokens(system_prompt, user_prompt)


def calculate_optimal_batch_size(messages: List[Dict[str, Any]], 
                                system_prompt: str,
                                user_prompt_template: str,
                                provider: str = "claude",
                                target_tokens_per_request: int = None) -> int:
    """
    Calculate optimal batch size to stay within token limits.
    
    Args:
        messages: List of messages to process
        system_prompt: System prompt template
        user_prompt_template: User prompt template
        provider: LLM provider name
        target_tokens_per_request: Override default target tokens per request
        
    Returns:
        Recommended batch size (minimum 1)
    """
    if not messages:
        return 1
    
    limits = RATE_LIMITS.get(provider, RATE_LIMITS["claude"])
    
    # Target tokens per request (leave room for multiple requests per minute)
    if target_tokens_per_request is None:
        # Assume we want to make ~10 requests per minute max
        target_tokens_per_request = min(
            limits.safe_tokens_per_minute // 10,
            15_000  # Reasonable max per request
        )
    
    # Estimate tokens for a single message
    sample_message = messages[0]
    single_message_tokens = estimate_message_batch_tokens(
        [sample_message], system_prompt, user_prompt_template
    )
    
    # Calculate how many messages can fit in target token count
    # Account for the fact that batch overhead doesn't scale linearly
    messages_per_batch = max(1, target_tokens_per_request // single_message_tokens)
    
    # Verify with actual batch estimation
    if messages_per_batch > 1 and len(messages) >= messages_per_batch:
        test_batch = messages[:messages_per_batch]
        actual_tokens = estimate_message_batch_tokens(
            test_batch, system_prompt, user_prompt_template
        )
        
        # If we're over target, reduce batch size
        while actual_tokens > target_tokens_per_request and messages_per_batch > 1:
            messages_per_batch -= 1
            test_batch = messages[:messages_per_batch]
            actual_tokens = estimate_message_batch_tokens(
                test_batch, system_prompt, user_prompt_template
            )
    
    return max(1, min(messages_per_batch, len(messages)))


def split_messages_by_token_limit(messages: List[Dict[str, Any]], 
                                system_prompt: str,
                                user_prompt_template: str,
                                provider: str = "claude") -> List[List[Dict[str, Any]]]:
    """
    Split messages into token-aware batches.
    
    Args:
        messages: List of messages to split
        system_prompt: System prompt template
        user_prompt_template: User prompt template
        provider: LLM provider name
        
    Returns:
        List of message batches, each within token limits
    """
    if not messages:
        return []
    
    batches = []
    remaining_messages = messages[:]
    
    while remaining_messages:
        # Calculate optimal batch size for remaining messages
        batch_size = calculate_optimal_batch_size(
            remaining_messages, system_prompt, user_prompt_template, provider
        )
        
        # Extract the batch
        batch = remaining_messages[:batch_size]
        batches.append(batch)
        
        # Remove processed messages
        remaining_messages = remaining_messages[batch_size:]
    
    return batches


def get_rate_limit_info(provider: str) -> TokenLimits:
    """Get rate limit information for a provider."""
    return RATE_LIMITS.get(provider, RATE_LIMITS["claude"])


def estimate_processing_time(total_messages: int, 
                           batch_size: int,
                           provider: str = "claude") -> float:
    """
    Estimate processing time based on rate limits.
    
    Args:
        total_messages: Total number of messages to process
        batch_size: Average batch size
        provider: LLM provider name
        
    Returns:
        Estimated processing time in minutes
    """
    limits = get_rate_limit_info(provider)
    
    total_requests = (total_messages + batch_size - 1) // batch_size  # Ceiling division
    
    # Calculate time needed based on request rate limits
    time_by_requests = total_requests / limits.max_requests_per_minute
    
    # For now, assume token limits are the main constraint
    # (could be enhanced to consider both constraints)
    
    return max(time_by_requests, 1.0)  # Minimum 1 minute