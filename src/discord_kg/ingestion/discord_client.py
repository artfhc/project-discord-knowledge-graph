"""Discord data ingestion - supports both API and exported JSON files"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import discord
from discord.ext import commands
from google.cloud import storage

logger = logging.getLogger(__name__)

class DiscordIngestor:
    """Handles Discord data ingestion from multiple sources"""
    
    def __init__(self, token: Optional[str] = None, server_id: Optional[int] = None):
        self.token = token
        self.server_id = server_id
        self.client = None
        self.gcs_client = None
    
    def setup_gcs_client(self, project_id: str, bucket_name: str):
        """Setup Google Cloud Storage client for reading exported files"""
        self.gcs_client = storage.Client(project=project_id)
        self.bucket = self.gcs_client.bucket(bucket_name)
        logger.info(f"GCS client configured for project: {project_id}, bucket: {bucket_name}")
    
    async def fetch_all_messages(self) -> List[Dict[str, Any]]:
        """Fetch all historical messages from all channels using Discord API"""
        # TODO: Implement Discord API message fetching
        # - Connect to Discord API
        # - Iterate through all channels
        # - Fetch message history with pagination
        # - Handle rate limits
        # - Return structured message data
        pass
    
    async def fetch_channel_messages(self, channel_id: int) -> List[Dict[str, Any]]:
        """Fetch messages from a specific channel using Discord API"""
        # TODO: Implement channel-specific message fetching
        pass
    
    def load_exported_json(self, file_path: Path) -> List[Dict[str, Any]]:
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
            
            logger.info(f"Loaded {len(messages)} messages from {file_path}")
            return self._normalize_exported_messages(messages, data.get('channel', {}))
            
        except Exception as e:
            logger.error(f"Failed to load exported JSON {file_path}: {str(e)}")
            return []
    
    def load_from_gcs(self, blob_path: str) -> List[Dict[str, Any]]:
        """Load messages from Google Cloud Storage"""
        if not self.gcs_client:
            raise ValueError("GCS client not configured. Call setup_gcs_client() first.")
        
        try:
            blob = self.bucket.blob(blob_path)
            content = blob.download_as_text()
            data = json.loads(content)
            
            if 'messages' in data:
                messages = data['messages']
            else:
                messages = data if isinstance(data, list) else []
                
            logger.info(f"Loaded {len(messages)} messages from GCS: {blob_path}")
            return self._normalize_exported_messages(messages, data.get('channel', {}))
            
        except Exception as e:
            logger.error(f"Failed to load from GCS {blob_path}: {str(e)}")
            return []
    
    def load_latest_exports(self, export_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load all messages from the latest export batch in GCS"""
        if not self.gcs_client:
            raise ValueError("GCS client not configured. Call setup_gcs_client() first.")
        
        try:
            # List all export directories
            prefix = 'discord-exports/'
            if export_date:
                prefix += f"{export_date}/"
            
            blobs = list(self.bucket.list_blobs(prefix=prefix))
            
            if not export_date:
                # Find the latest export timestamp
                timestamps = set()
                for blob in blobs:
                    parts = blob.name.split('/')
                    if len(parts) >= 2 and parts[1]:
                        timestamps.add(parts[1])
                
                if not timestamps:
                    logger.warning("No export timestamps found")
                    return []
                
                latest_timestamp = max(timestamps)
                logger.info(f"Loading latest export: {latest_timestamp}")
            else:
                latest_timestamp = export_date
            
            # Load all JSON files from the latest export
            all_messages = []
            export_blobs = [b for b in blobs if latest_timestamp in b.name and b.name.endswith('.json')]
            
            for blob in export_blobs:
                if 'manifest.json' in blob.name:
                    continue  # Skip manifest files
                    
                messages = self.load_from_gcs(blob.name)
                all_messages.extend(messages)
            
            logger.info(f"Loaded total of {len(all_messages)} messages from {len(export_blobs)} files")
            return all_messages
            
        except Exception as e:
            logger.error(f"Failed to load latest exports: {str(e)}")
            return []
    
    def _normalize_exported_messages(self, messages: List[Dict], channel_info: Dict) -> List[Dict[str, Any]]:
        """Normalize DiscordChatExporter format to our internal format"""
        normalized = []
        
        for msg in messages:
            try:
                normalized_msg = {
                    'id': msg.get('id'),
                    'channel_id': channel_info.get('id') or msg.get('channelId'),
                    'channel_name': channel_info.get('name') or msg.get('channelName'),
                    'author_id': msg.get('author', {}).get('id'),
                    'author_name': msg.get('author', {}).get('name'),
                    'author_display_name': msg.get('author', {}).get('displayName'),
                    'content': msg.get('content', ''),
                    'timestamp': msg.get('timestamp'),
                    'message_type': msg.get('type', 'default'),
                    'attachments': msg.get('attachments', []),
                    'embeds': msg.get('embeds', []),
                    'reactions': msg.get('reactions', []),
                    'reply_to': msg.get('reference', {}).get('messageId') if msg.get('reference') else None,
                    'raw_data': msg  # Keep original for reference
                }
                
                # Only include messages with actual content
                if normalized_msg['content'] or normalized_msg['attachments'] or normalized_msg['embeds']:
                    normalized.append(normalized_msg)
                    
            except Exception as e:
                logger.warning(f"Failed to normalize message {msg.get('id', 'unknown')}: {str(e)}")
                continue
        
        return normalized