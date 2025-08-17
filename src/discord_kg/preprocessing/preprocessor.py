"""
Local preprocessor for Discord messages with complete preprocessing pipeline.
Handles preservation, normalization, segmentation, and classification.
"""

import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import hashlib
from pathlib import Path


@dataclass
class PreprocessedMessage:
    """Complete preprocessed Discord message structure"""
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
    
    # Preserved metadata
    original_timestamp: str
    author_id: str
    author_roles: List[str]
    mentions: List[str]
    attachments: List[Dict[str, Any]]
    reactions: List[Dict[str, Any]]
    is_bot: bool
    is_pinned: bool
    reply_to: Optional[str]


class DiscordPreprocessor:
    """Complete preprocessing pipeline for Discord messages"""
    
    def __init__(self):
        self.segment_cache = {}  # Cache for segment grouping
        
    def preserve_metadata(self, message: Dict) -> Dict[str, Any]:
        """Extract and preserve all important metadata from raw message"""
        author = message.get("author", {})
        
        # Extract author roles
        roles = []
        for role in author.get("roles", []):
            if isinstance(role, dict):
                roles.append(role.get("name", ""))
            else:
                roles.append(str(role))
        
        # Extract mentions
        mentions = []
        for mention in message.get("mentions", []):
            if isinstance(mention, dict):
                mentions.append(mention.get("name", mention.get("id", "")))
            else:
                mentions.append(str(mention))
        
        # Extract attachments info
        attachments = []
        for attachment in message.get("attachments", []):
            if isinstance(attachment, dict):
                attachments.append({
                    "filename": attachment.get("fileName", ""),
                    "url": attachment.get("url", ""),
                    "size": attachment.get("fileSizeBytes", 0)
                })
        
        # Extract reactions
        reactions = []
        for reaction in message.get("reactions", []):
            if isinstance(reaction, dict):
                reactions.append({
                    "emoji": reaction.get("emoji", {}).get("name", ""),
                    "count": reaction.get("count", 0)
                })
        
        return {
            "original_timestamp": message.get("timestamp", ""),
            "author_id": author.get("id", ""),
            "author_roles": roles,
            "mentions": mentions,
            "attachments": attachments,
            "reactions": reactions,
            "is_bot": author.get("isBot", False),
            "is_pinned": message.get("isPinned", False),
            "reply_to": message.get("reference", {}).get("messageId") if message.get("reference") else None
        }
    
    def normalize_timestamp(self, timestamp_str: str) -> str:
        """Convert timestamp to ISO 8601 UTC format"""
        if not timestamp_str:
            return datetime.now(timezone.utc).isoformat()
        
        try:
            # Handle various timestamp formats
            if timestamp_str.endswith('Z'):
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            elif '+' in timestamp_str or '-' in timestamp_str[-6:]:
                dt = datetime.fromisoformat(timestamp_str)
            else:
                # Assume UTC if no timezone info
                dt = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
            
            # Convert to UTC and return ISO format
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            # Fallback to current time if parsing fails
            return datetime.now(timezone.utc).isoformat()
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize message text while preserving meaning"""
        if not text:
            return ""
        
        # Convert to lowercase
        clean = text.lower()
        
        # Normalize whitespace - remove excessive line breaks and spaces
        clean = re.sub(r'\n\s*\n\s*\n+', '\n\n', clean)  # Max 2 consecutive newlines
        clean = re.sub(r'[ \t]+', ' ', clean)  # Normalize spaces and tabs
        clean = clean.strip()
        
        # Preserve Discord formatting but make it readable
        clean = re.sub(r'<@!?(\d+)>', r'@user\1', clean)  # User mentions
        clean = re.sub(r'<#(\d+)>', r'#channel\1', clean)  # Channel mentions
        clean = re.sub(r'<@&(\d+)>', r'@role\1', clean)   # Role mentions
        clean = re.sub(r'<:(\w+):\d+>', r':\1:', clean)   # Custom emojis
        
        return clean
    
    def generate_segment_id(self, message: Dict, thread_name: Optional[str], 
                          channel_name: str, author: str, timestamp: str) -> str:
        """Generate segment ID for message grouping"""
        
        if thread_name:
            # Thread-based segmentation
            thread_clean = re.sub(r'[^a-zA-Z0-9]', '-', thread_name.lower())
            return f"thread-{thread_clean}"
        
        # Channel + author based segmentation with time window
        # Create a hash for the base segment
        segment_base = f"{channel_name}-{author}"
        
        # For time-based grouping, use hour windows
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_window = dt.strftime("%Y%m%d-%H")  # YYYYMMDD-HH format
        except:
            time_window = "unknown"
        
        segment_key = f"{segment_base}-{time_window}"
        
        # Create short hash for uniqueness
        hash_obj = hashlib.md5(segment_key.encode())
        short_hash = hash_obj.hexdigest()[:8]
        
        return f"segment-{short_hash}"
    
    def extract_thread_name(self, message: Dict) -> Optional[str]:
        """Extract thread name from message"""
        # Check for thread info in message
        if "thread" in message and message["thread"]:
            thread_info = message["thread"]
            if isinstance(thread_info, dict):
                return thread_info.get("name")
            else:
                return str(thread_info)
        
        # Check for reference to thread
        if "reference" in message and message["reference"]:
            ref = message["reference"]
            if isinstance(ref, dict) and "channelId" in ref:
                # This might be a thread reference
                return f"thread-{ref['channelId']}"
        
        return None
    
    def group_messages_by_segments(self, messages: List[Dict], 
                                 max_time_gap_minutes: int = 5) -> Dict[str, List[Dict]]:
        """Group messages into segments using various heuristics"""
        segments = {}
        
        for message in messages:
            # Basic message info
            author = message.get("author", {}).get("name", "unknown")
            timestamp = message.get("timestamp", "")
            channel_name = message.get("channel", {}).get("name", "unknown")
            
            # Extract thread info
            thread_name = self.extract_thread_name(message)
            
            # Generate segment ID
            segment_id = self.generate_segment_id(
                message, thread_name, channel_name, author, timestamp
            )
            
            # Add to segment
            if segment_id not in segments:
                segments[segment_id] = []
            segments[segment_id].append(message)
        
        return segments
    
    def process_message(self, message: Dict, segment_id: str, 
                       channel_name: str, msg_type: str = "alert", 
                       confidence: float = 0.5) -> PreprocessedMessage:
        """Process a single message through the complete pipeline"""
        
        # Extract basic info
        message_id = message.get("id", "")
        content = message.get("content", "")
        author_info = message.get("author", {})
        author = author_info.get("name", "unknown")
        timestamp = message.get("timestamp", "")
        
        # Normalize timestamp
        normalized_timestamp = self.normalize_timestamp(timestamp)
        
        # Clean text
        clean_text = self.clean_text(content)
        
        # Extract thread info
        thread_name = self.extract_thread_name(message)
        
        # Preserve metadata
        metadata = self.preserve_metadata(message)
        
        # Create preprocessed message
        return PreprocessedMessage(
            message_id=message_id,
            segment_id=segment_id,
            thread=thread_name,
            channel=channel_name,
            author=author,
            timestamp=normalized_timestamp,
            type=msg_type,
            confidence=confidence,
            content=content,
            clean_text=clean_text,
            **metadata
        )
    
    def process_discord_export(self, file_path: str) -> List[PreprocessedMessage]:
        """Process complete Discord export through preprocessing pipeline"""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        messages = data.get("messages", [])
        channel_name = data.get("channel", {}).get("name", "unknown")
        
        print(f"Processing {len(messages)} messages from #{channel_name}...")
        
        # Group messages into segments
        segments = self.group_messages_by_segments(messages)
        print(f"Created {len(segments)} message segments")
        
        # Process each message
        preprocessed_messages = []
        
        for segment_id, segment_messages in segments.items():
            for message in segment_messages:
                # Skip empty messages
                if not message.get("content", "").strip():
                    continue
                
                # Process message (classification will be added later)
                preprocessed_msg = self.process_message(
                    message, segment_id, channel_name
                )
                
                preprocessed_messages.append(preprocessed_msg)
        
        return preprocessed_messages
    
    def save_results(self, preprocessed_messages: List[PreprocessedMessage], 
                    output_path: str):
        """Save preprocessed messages to JSONL format"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for msg in preprocessed_messages:
                json.dump(asdict(msg), f, ensure_ascii=False)
                f.write('\n')
        
        print(f"Saved {len(preprocessed_messages)} preprocessed messages to {output_path}")
    
    def print_stats(self, preprocessed_messages: List[PreprocessedMessage]):
        """Print preprocessing statistics"""
        segments = set(msg.segment_id for msg in preprocessed_messages)
        authors = set(msg.author for msg in preprocessed_messages)
        threads = set(msg.thread for msg in preprocessed_messages if msg.thread)
        
        print("\nPreprocessing Statistics:")
        print("=" * 40)
        print(f"Total messages: {len(preprocessed_messages)}")
        print(f"Unique segments: {len(segments)}")
        print(f"Unique authors: {len(authors)}")
        print(f"Messages with threads: {len([m for m in preprocessed_messages if m.thread])}")
        print(f"Bot messages: {len([m for m in preprocessed_messages if m.is_bot])}")
        print(f"Pinned messages: {len([m for m in preprocessed_messages if m.is_pinned])}")
        print(f"Messages with attachments: {len([m for m in preprocessed_messages if m.attachments])}")


def main():
    """Main function for local testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Preprocess Discord messages")
    parser.add_argument("input_file", help="Path to Discord export JSON file")
    parser.add_argument("--output", "-o", default="preprocessed_messages.jsonl",
                       help="Output JSONL file path")
    
    args = parser.parse_args()
    
    # Initialize preprocessor
    preprocessor = DiscordPreprocessor()
    
    # Process messages
    preprocessed_messages = preprocessor.process_discord_export(args.input_file)
    
    # Save results
    preprocessor.save_results(preprocessed_messages, args.output)
    
    # Print statistics
    preprocessor.print_stats(preprocessed_messages)


if __name__ == "__main__":
    main()