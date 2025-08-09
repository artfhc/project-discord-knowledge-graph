#!/usr/bin/env python3
"""
Simple script to process exported Discord JSON files without Discord API dependencies
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('processing.log')
        ]
    )

def load_exported_json(file_path: Path, logger) -> List[Dict[str, Any]]:
    """Load messages from DiscordChatExporter JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # DiscordChatExporter format has messages in 'messages' array
        if 'messages' in data:
            messages = data['messages']
        else:
            # Fallback if it's just an array of messages
            messages = data if isinstance(data, list) else []
        
        logger.info(f"Loaded {len(messages)} messages from {file_path.name}")
        return normalize_messages(messages, data.get('channel', {}), logger)
        
    except Exception as e:
        logger.error(f"Failed to load exported JSON {file_path}: {str(e)}")
        return []

def normalize_messages(messages: List[Dict], channel_info: Dict, logger) -> List[Dict[str, Any]]:
    """Normalize DiscordChatExporter format to our internal format"""
    normalized = []
    
    for msg in messages:
        try:
            normalized_msg = {
                'id': msg.get('id'),
                'channel_id': channel_info.get('id') or msg.get('channelId'),
                'channel_name': channel_info.get('name') or msg.get('channelName'),
                'guild_id': channel_info.get('guild', {}).get('id'),
                'guild_name': channel_info.get('guild', {}).get('name'),
                'author_id': msg.get('author', {}).get('id'),
                'author_name': msg.get('author', {}).get('name'),
                'author_display_name': msg.get('author', {}).get('displayName'),
                'content': msg.get('content', ''),
                'timestamp': msg.get('timestamp'),
                'message_type': msg.get('type', 'Default'),
                'attachments': msg.get('attachments', []),
                'embeds': msg.get('embeds', []),
                'reactions': msg.get('reactions', []),
                'reply_to': msg.get('reference', {}).get('messageId') if msg.get('reference') else None,
                'raw_data': msg
            }
            
            # Only include messages with actual content
            if normalized_msg['content'] or normalized_msg['attachments'] or normalized_msg['embeds']:
                normalized.append(normalized_msg)
                
        except Exception as e:
            logger.warning(f"Failed to normalize message {msg.get('id', 'unknown')}: {str(e)}")
            continue
    
    return normalized

def process_messages_simple(messages: List[Dict[str, Any]], logger) -> Dict[str, Any]:
    """Simple message processing without full pipeline dependencies"""
    
    # Basic statistics and processing
    total_messages = len(messages)
    
    # Filter out system messages and empty content
    content_messages = [msg for msg in messages 
                       if msg.get('content') and msg.get('message_type') == 'Default']
    
    # Extract basic statistics
    channels = set(msg.get('channel_name') for msg in messages if msg.get('channel_name'))
    authors = set(msg.get('author_name') for msg in messages if msg.get('author_name'))
    
    # Simple content analysis
    total_chars = sum(len(msg.get('content', '')) for msg in content_messages)
    avg_message_length = total_chars / len(content_messages) if content_messages else 0
    
    # Find messages with attachments or embeds
    media_messages = [msg for msg in messages 
                     if msg.get('attachments') or msg.get('embeds')]
    
    # Simple "knowledge" extraction - messages with questions
    question_indicators = ['?', 'how', 'what', 'why', 'when', 'where', 'who']
    potential_questions = []
    
    for msg in content_messages:
        content_lower = msg.get('content', '').lower()
        if any(indicator in content_lower for indicator in question_indicators):
            potential_questions.append(msg)
    
    results = {
        'summary': {
            'total_messages': total_messages,
            'content_messages': len(content_messages),
            'channels': len(channels),
            'authors': len(authors),
            'media_messages': len(media_messages),
            'potential_questions': len(potential_questions),
            'avg_message_length': round(avg_message_length, 2),
            'total_characters': total_chars
        },
        'channels_list': list(channels),
        'authors_list': list(authors),
        'sample_questions': potential_questions[:5],  # First 5 questions
    }
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Process exported Discord JSON files")
    parser.add_argument('directory', help='Directory containing exported JSON files')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--output', help='Output file for results (JSON format)')
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("🔄 Starting Discord JSON file processing")
    
    try:
        directory = Path(args.directory)
        if not directory.exists():
            logger.error(f"Directory does not exist: {directory}")
            return 1
        
        # Find JSON files
        json_files = list(directory.glob('*.json'))
        if not json_files:
            logger.error(f"No JSON files found in: {directory}")
            return 1
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        all_messages = []
        
        # Process each file
        for json_file in json_files:
            if 'manifest.json' in json_file.name:
                continue  # Skip manifest files
                
            logger.info(f"Processing: {json_file.name}")
            messages = load_exported_json(json_file, logger)
            all_messages.extend(messages)
        
        if not all_messages:
            logger.warning("No messages loaded from files")
            return 0
        
        logger.info(f"📊 Total loaded messages: {len(all_messages)}")
        
        # Process messages
        logger.info("🔄 Processing messages...")
        results = process_messages_simple(all_messages, logger)
        
        # Log results
        summary = results['summary']
        logger.info("📈 Processing Results:")
        logger.info(f"  - Total messages: {summary['total_messages']}")
        logger.info(f"  - Content messages: {summary['content_messages']}")
        logger.info(f"  - Channels: {summary['channels']}")
        logger.info(f"  - Authors: {summary['authors']}")
        logger.info(f"  - Media messages: {summary['media_messages']}")
        logger.info(f"  - Potential questions: {summary['potential_questions']}")
        logger.info(f"  - Avg message length: {summary['avg_message_length']} chars")
        
        # Save results if output specified
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"💾 Results saved to: {output_path}")
        
        logger.info("✅ Processing completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())