"""
Local message classifier using TinyBERT for Discord message preprocessing.
Classifies messages into: question, answer, alert, strategy
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import pandas as pd
from tqdm import tqdm


@dataclass
class ClassifiedMessage:
    """Structured output for classified Discord messages"""
    message_id: str
    segment_id: str
    thread: Optional[str]
    channel: str
    author: str
    timestamp: str
    type: str
    confidence: float
    content: str
    clean_text: str


class DiscordMessageClassifier:
    """Zero-shot classifier for Discord messages using BART-MNLI"""
    
    def __init__(self, model_name: str = "facebook/bart-large-mnli", batch_size: int = 16):
        """Initialize classifier with zero-shot classification model"""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.batch_size = batch_size
        print(f"Using device: {self.device}")
        print(f"Batch size: {batch_size}")
        
        # Use zero-shot classification pipeline with batch support
        self.classifier = pipeline(
            "zero-shot-classification",
            model=model_name,
            device=0 if torch.cuda.is_available() else -1,
            batch_size=batch_size
        )
        
        # Label mapping for Discord message types
        self.labels = ["question", "answer", "alert", "strategy", "signal", "performance", "analysis", "discussion"]
        
        # Define what each label means for better classification
        self.label_descriptions = {
            "question": "asking for information, help, or clarification",
            "answer": "providing information, explanation, or response to a question", 
            "alert": "notification, warning, announcement, or urgent message",
            "strategy": "discussion about trading strategies, symphony creation, or strategic planning",
            "signal": "specific trade calls, buy/sell recommendations, entry/exit points, or actionable trading advice",
            "performance": "portfolio updates, P&L reports, backtest results, or strategy performance metrics",
            "analysis": "market analysis, technical analysis, fundamental research, or data-driven insights",
            "discussion": "general conversation, opinions, debates, or casual trading discussion"
        }
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize message text"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove Discord-specific formatting but preserve content
        text = re.sub(r'<@!?\d+>', '[mention]', text)  # User mentions
        text = re.sub(r'<#\d+>', '[channel]', text)    # Channel mentions
        text = re.sub(r'<:\w+:\d+>', '[emoji]', text)  # Custom emojis
        
        return text
    
    def clean_texts_batch(self, texts: List[str]) -> List[str]:
        """Clean multiple texts using vectorized operations for better performance"""
        if not texts:
            return []
        
        # Create pandas Series for vectorized string operations
        series = pd.Series(texts).fillna("")
        
        # Convert to lowercase
        series = series.str.lower()
        
        # Remove excessive whitespace
        series = series.str.replace(r'\s+', ' ', regex=True)
        series = series.str.strip()
        
        # Remove Discord-specific formatting but preserve content
        series = series.str.replace(r'<@!?\d+>', '[mention]', regex=True)  # User mentions
        series = series.str.replace(r'<#\d+>', '[channel]', regex=True)    # Channel mentions
        series = series.str.replace(r'<:\w+:\d+>', '[emoji]', regex=True)  # Custom emojis
        
        return series.tolist()
    
    def extract_thread_name(self, message: Dict) -> Optional[str]:
        """Extract thread name from message if available"""
        if "thread" in message and message["thread"]:
            return message["thread"].get("name")
        return None
    
    def generate_segment_id(self, message: Dict, thread_name: Optional[str]) -> str:
        """Generate segment ID for message grouping"""
        if thread_name:
            # Use thread-based segmentation
            return f"thread-{re.sub(r'[^a-zA-Z0-9-]', '-', thread_name)}"
        else:
            # Use channel-based segmentation
            channel_name = message.get("channel", {}).get("name", "unknown")
            author = message.get("author", {}).get("name", "unknown")
            return f"channel-{channel_name}-{author}"
    
    def classify_message(self, text: str) -> Tuple[str, float]:
        """Classify a single message and return type with confidence"""
        if not text.strip():
            return "alert", 0.5  # Default for empty messages
        
        # Get zero-shot predictions
        results = self.classifier(text, self.labels)
        
        # Extract best prediction - zero-shot returns different format
        best_label = results['labels'][0]  # First label is highest scoring
        best_score = results['scores'][0]  # First score is highest
        
        return best_label, best_score
    
    def classify_messages_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        """Classify multiple messages in batch for better performance"""
        if not texts:
            return []
        
        # Filter out empty texts and track indices
        non_empty_texts = []
        empty_indices = set()
        
        for i, text in enumerate(texts):
            if text.strip():
                non_empty_texts.append(text)
            else:
                empty_indices.add(i)
        
        # Batch classify non-empty texts
        results = []
        if non_empty_texts:
            batch_results = self.classifier(non_empty_texts, self.labels)
            # Handle single vs batch results
            if isinstance(batch_results, list):
                results = [(r['labels'][0], r['scores'][0]) for r in batch_results]
            else:
                results = [(batch_results['labels'][0], batch_results['scores'][0])]
        
        # Reconstruct full results with defaults for empty texts
        final_results = []
        result_idx = 0
        
        for i in range(len(texts)):
            if i in empty_indices:
                final_results.append(("alert", 0.5))
            else:
                final_results.append(results[result_idx])
                result_idx += 1
        
        return final_results
    
    def process_discord_export(self, file_path: str) -> List[ClassifiedMessage]:
        """Process Discord export JSON and return classified messages with batch processing"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        messages = data.get("messages", [])
        classified_messages = []
        
        print(f"Processing {len(messages)} messages in batches of {self.batch_size}...")
        
        # Process messages in batches
        for i in tqdm(range(0, len(messages), self.batch_size), desc="Processing batches"):
            batch = messages[i:i + self.batch_size]
            
            # Pre-process batch: extract info and metadata
            batch_data = []
            batch_contents = []
            
            for message in batch:
                # Extract basic info
                message_id = message.get("id", "")
                content = message.get("content", "")
                author_info = message.get("author", {})
                author = author_info.get("name", "unknown")
                
                # Extract additional metadata
                thread_name = self.extract_thread_name(message)
                segment_id = self.generate_segment_id(message, thread_name)
                
                # Format timestamp
                timestamp = message.get("timestamp", "")
                if timestamp:
                    try:
                        # Parse and format to ISO 8601 UTC
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamp = dt.isoformat()
                    except:
                        pass  # Keep original if parsing fails
                
                batch_data.append({
                    'message_id': message_id,
                    'segment_id': segment_id,
                    'thread': thread_name,
                    'channel': data.get("channel", {}).get("name", "unknown"),
                    'author': author,
                    'timestamp': timestamp,
                    'content': content
                })
                batch_contents.append(content)
            
            # Batch clean all texts at once
            batch_clean_texts = self.clean_texts_batch(batch_contents)
            
            # Add clean texts to batch data
            for msg_data, clean_text in zip(batch_data, batch_clean_texts):
                msg_data['clean_text'] = clean_text
            
            # Batch classify all texts at once
            classifications = self.classify_messages_batch(batch_clean_texts)
            
            # Create classified messages
            for msg_data, (msg_type, confidence) in zip(batch_data, classifications):
                # Skip empty messages
                if not msg_data['clean_text']:
                    continue
                
                classified_msg = ClassifiedMessage(
                    message_id=msg_data['message_id'],
                    segment_id=msg_data['segment_id'],
                    thread=msg_data['thread'],
                    channel=msg_data['channel'],
                    author=msg_data['author'],
                    timestamp=msg_data['timestamp'],
                    type=msg_type,
                    confidence=confidence,
                    content=msg_data['content'],
                    clean_text=msg_data['clean_text']
                )
                
                classified_messages.append(classified_msg)
        
        return classified_messages
    
    def save_results(self, classified_messages: List[ClassifiedMessage], output_path: str):
        """Save classified messages to JSONL format"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for msg in classified_messages:
                json.dump(asdict(msg), f, ensure_ascii=False)
                f.write('\n')
        
        print(f"Saved {len(classified_messages)} classified messages to {output_path}")
    
    def print_stats(self, classified_messages: List[ClassifiedMessage]):
        """Print classification statistics"""
        df = pd.DataFrame([asdict(msg) for msg in classified_messages])
        
        print("\nClassification Statistics:")
        print("=" * 40)
        print(df['type'].value_counts())
        print(f"\nAverage confidence: {df['confidence'].mean():.3f}")
        print(f"Messages with confidence > 0.8: {(df['confidence'] > 0.8).sum()}")
        print(f"Total messages processed: {len(df)}")


def main():
    """Main function for local testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Classify Discord messages using TinyBERT")
    parser.add_argument("input_file", help="Path to Discord export JSON file")
    parser.add_argument("--output", "-o", default="classified_messages.jsonl", 
                       help="Output JSONL file path")
    parser.add_argument("--model", default="huawei-noah/TinyBERT_General_4L_312D",
                       help="HuggingFace model name")
    
    args = parser.parse_args()
    
    # Initialize classifier
    classifier = DiscordMessageClassifier(model_name=args.model)
    
    # Process messages
    classified_messages = classifier.process_discord_export(args.input_file)
    
    # Save results
    classifier.save_results(classified_messages, args.output)
    
    # Print statistics
    classifier.print_stats(classified_messages)


if __name__ == "__main__":
    main()