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
    
    def __init__(self, model_name: str = "facebook/bart-large-mnli"):
        """Initialize classifier with zero-shot classification model"""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        
        # Use zero-shot classification pipeline
        self.classifier = pipeline(
            "zero-shot-classification",
            model=model_name,
            device=0 if torch.cuda.is_available() else -1
        )
        
        # Label mapping for Discord message types
        self.labels = ["question", "answer", "alert", "strategy"]
        
        # Define what each label means for better classification
        self.label_descriptions = {
            "question": "asking for information, help, or clarification",
            "answer": "providing information, explanation, or response to a question", 
            "alert": "notification, warning, announcement, or urgent message",
            "strategy": "discussion about plans, recommendations, or strategic thinking"
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
    
    def process_discord_export(self, file_path: str) -> List[ClassifiedMessage]:
        """Process Discord export JSON and return classified messages"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        messages = data.get("messages", [])
        classified_messages = []
        
        print(f"Processing {len(messages)} messages...")
        
        for message in tqdm(messages, desc="Classifying messages"):
            # Extract basic info
            message_id = message.get("id", "")
            content = message.get("content", "")
            author_info = message.get("author", {})
            author = author_info.get("name", "unknown")
            
            # Clean and classify
            clean_text = self.clean_text(content)
            if not clean_text:
                continue  # Skip empty messages
            
            msg_type, confidence = self.classify_message(clean_text)
            
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
            
            # Create classified message
            classified_msg = ClassifiedMessage(
                message_id=message_id,
                segment_id=segment_id,
                thread=thread_name,
                channel=data.get("channel", {}).get("name", "unknown"),
                author=author,
                timestamp=timestamp,
                type=msg_type,
                confidence=confidence,
                content=content,
                clean_text=clean_text
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