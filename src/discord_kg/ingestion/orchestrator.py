"""Orchestrator for Discord message ingestion and processing pipeline"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from .discord_chat_exporter import DiscordChatExporterIngestor
from .discord_client import DiscordIngestor
from .storage import B2Storage

logger = logging.getLogger(__name__)

class IngestionOrchestrator:
    """Orchestrates the complete Discord message ingestion pipeline"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the ingestion orchestrator
        
        Args:
            config: Configuration dictionary with ingestion settings
        """
        self.config = config or {}
        self.storage_backend = None
        
        # Initialize storage if configured
        if self.config.get('storage'):
            storage_config = self.config['storage']
            if storage_config['type'] == 'b2':
                self.storage_backend = B2Storage(
                    storage_config['key_id'],
                    storage_config['application_key'],
                    storage_config['bucket_name']
                )
    
    def ingest_from_discord_chat_exporter(
        self,
        discord_token: str,
        channel_ids: Optional[List[str]] = None,
        guild_id: Optional[str] = None,
        exporter_path: Optional[str] = None,
        **export_kwargs
    ) -> List[Dict[str, Any]]:
        """
        Ingest Discord messages using DiscordChatExporter
        
        Args:
            discord_token: Discord token for authentication
            channel_ids: List of channel IDs to export (for channel-specific export)
            guild_id: Guild ID for full server export
            exporter_path: Path to DiscordChatExporter executable
            **export_kwargs: Additional export options
            
        Returns:
            List of normalized message dictionaries
        """
        logger.info("Starting DiscordChatExporter ingestion")
        
        try:
            # Initialize the DiscordChatExporter client
            exporter_ingestor = DiscordChatExporterIngestor(
                discord_token, 
                exporter_path
            )
            
            # Determine ingestion mode
            if guild_id:
                logger.info(f"Ingesting entire guild: {guild_id}")
                messages = exporter_ingestor.ingest_guild(guild_id, **export_kwargs)
                
            elif channel_ids:
                logger.info(f"Ingesting {len(channel_ids)} channels")
                messages = exporter_ingestor.ingest_channels(channel_ids, **export_kwargs)
                
            else:
                raise ValueError("Must specify either channel_ids or guild_id")
            
            logger.info(f"Successfully ingested {len(messages)} messages")
            
            # Store messages if storage backend is configured
            if self.storage_backend and messages:
                self._store_messages(messages)
            
            return messages
            
        except Exception as e:
            logger.error(f"DiscordChatExporter ingestion failed: {str(e)}")
            raise
    
    async def ingest_from_api(
        self,
        discord_token: str,
        server_id: int,
        channel_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Ingest Discord messages using Discord API directly
        
        Args:
            discord_token: Discord token for authentication
            server_id: Discord server ID
            channel_ids: Optional list of specific channel IDs
            
        Returns:
            List of normalized message dictionaries
        """
        logger.info("Starting Discord API ingestion")
        
        try:
            # Initialize the Discord API client
            api_ingestor = DiscordIngestor(discord_token, server_id)
            
            if channel_ids:
                # Ingest specific channels
                all_messages = []
                for channel_id in channel_ids:
                    messages = await api_ingestor.fetch_channel_messages(channel_id)
                    all_messages.extend(messages)
                messages = all_messages
            else:
                # Ingest all channels
                messages = await api_ingestor.fetch_all_messages()
            
            logger.info(f"Successfully ingested {len(messages)} messages via API")
            
            # Store messages if storage backend is configured
            if self.storage_backend and messages:
                self._store_messages(messages)
            
            return messages
            
        except Exception as e:
            logger.error(f"Discord API ingestion failed: {str(e)}")
            raise
    
    def ingest_from_local_files(
        self,
        file_paths: List[Path],
        format: str = "discord_chat_exporter"
    ) -> List[Dict[str, Any]]:
        """
        Ingest Discord messages from local files
        
        Args:
            file_paths: List of paths to exported JSON files
            format: Format of the files ("discord_chat_exporter" or "raw")
            
        Returns:
            List of normalized message dictionaries
        """
        logger.info(f"Starting local file ingestion from {len(file_paths)} files")
        
        try:
            all_messages = []
            
            # Initialize appropriate ingestor
            if format == "discord_chat_exporter":
                ingestor = DiscordIngestor()
                
                for file_path in file_paths:
                    if not file_path.exists():
                        logger.warning(f"File not found: {file_path}")
                        continue
                    
                    messages = ingestor.load_exported_json(file_path)
                    all_messages.extend(messages)
                    logger.info(f"Loaded {len(messages)} messages from {file_path.name}")
            
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Successfully ingested {len(all_messages)} messages from local files")
            
            # Store messages if storage backend is configured
            if self.storage_backend and all_messages:
                self._store_messages(all_messages)
            
            return all_messages
            
        except Exception as e:
            logger.error(f"Local file ingestion failed: {str(e)}")
            raise
    
    def ingest_from_gcs(
        self,
        gcp_project: str,
        bucket_name: str,
        export_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Ingest Discord messages from Google Cloud Storage
        
        Args:
            gcp_project: Google Cloud Project ID
            bucket_name: GCS bucket name
            export_date: Specific export date to load (YYYYMMDD_HHMMSS)
            
        Returns:
            List of normalized message dictionaries
        """
        logger.info(f"Starting GCS ingestion from {bucket_name}")
        
        try:
            # Initialize GCS ingestor
            ingestor = DiscordIngestor()
            ingestor.setup_gcs_client(gcp_project, bucket_name)
            
            # Load messages from GCS
            messages = ingestor.load_latest_exports(export_date)
            
            logger.info(f"Successfully ingested {len(messages)} messages from GCS")
            
            # Store messages if storage backend is configured
            if self.storage_backend and messages:
                self._store_messages(messages)
            
            return messages
            
        except Exception as e:
            logger.error(f"GCS ingestion failed: {str(e)}")
            raise
    
    def process_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process ingested messages through the complete pipeline
        
        Args:
            messages: List of normalized message dictionaries
            
        Returns:
            Processing results and statistics
        """
        logger.info(f"Starting message processing for {len(messages)} messages")
        
        try:
            # Import processing modules (lazy import to avoid circular dependencies)
            from ..preprocessing.cleaner import MessageCleaner
            from ..preprocessing.classifier import MessageClassifier
            from ..extraction.triple_extractor import TripleExtractor
            
            # Initialize processors
            cleaner = MessageCleaner()
            classifier = MessageClassifier()
            extractor = TripleExtractor()
            
            # Processing pipeline
            logger.info("Phase 1: Cleaning messages")
            cleaned_messages = []
            for msg in messages:
                cleaned = cleaner.clean_message(msg)
                if cleaned:  # Only keep non-empty messages
                    cleaned_messages.append(cleaned)
            
            logger.info(f"Cleaned {len(cleaned_messages)}/{len(messages)} messages")
            
            logger.info("Phase 2: Classifying messages")
            classified_messages = []
            for msg in cleaned_messages:
                classified = classifier.classify_message(msg)
                classified_messages.append(classified)
            
            logger.info("Phase 3: Extracting knowledge triples")
            all_triples = []
            for msg in classified_messages:
                triples = extractor.extract_triples(msg)
                all_triples.extend(triples)
            
            # Create processing summary
            processing_summary = {
                'input_messages': len(messages),
                'cleaned_messages': len(cleaned_messages),
                'classified_messages': len(classified_messages),
                'extracted_triples': len(all_triples),
                'channels': len(set(msg.get('channel_name') for msg in messages)),
                'authors': len(set(msg.get('author_name') for msg in messages)),
                'processing_timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Processing completed: {processing_summary}")
            
            return {
                'messages': classified_messages,
                'triples': all_triples,
                'summary': processing_summary
            }
            
        except Exception as e:
            logger.error(f"Message processing failed: {str(e)}")
            raise
    
    def _store_messages(self, messages: List[Dict[str, Any]]):
        """Store messages using configured storage backend"""
        if not self.storage_backend:
            logger.warning("No storage backend configured")
            return
        
        try:
            # Group messages by channel for storage
            channels = {}
            for msg in messages:
                channel_id = msg.get('channel_id')
                if channel_id:
                    if channel_id not in channels:
                        channels[channel_id] = []
                    channels[channel_id].append(msg)
            
            # Store each channel's messages
            for channel_id, channel_messages in channels.items():
                # Use first message to get server info
                server_id = channel_messages[0].get('guild_id', 'unknown')
                
                storage_key = self.storage_backend.store_messages(
                    channel_messages, 
                    server_id, 
                    channel_id
                )
                
                logger.info(f"Stored {len(channel_messages)} messages for channel {channel_id} at {storage_key}")
                
        except Exception as e:
            logger.error(f"Failed to store messages: {str(e)}")
            # Don't raise - storage failure shouldn't break the pipeline