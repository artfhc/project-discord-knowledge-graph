"""Integration with DiscordChatExporter for message ingestion"""

import json
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)

class DiscordChatExporterClient:
    """Client for running DiscordChatExporter CLI and processing results"""
    
    def __init__(self, token: str, exporter_path: Optional[str] = None):
        """
        Initialize DiscordChatExporter client
        
        Args:
            token: Discord token (user or bot token)
            exporter_path: Path to DiscordChatExporter.Cli executable
        """
        self.token = token
        self.exporter_path = exporter_path or self._find_exporter()
        
        if not self.exporter_path or not Path(self.exporter_path).exists():
            raise ValueError("DiscordChatExporter.Cli not found. Please specify exporter_path or ensure it's in PATH")
    
    def _find_exporter(self) -> Optional[str]:
        """Try to find DiscordChatExporter.Cli in common locations"""
        possible_names = [
            'DiscordChatExporter.Cli',
            'DiscordChatExporter.Cli.exe',
            'dotnet DiscordChatExporter.Cli.dll'
        ]
        
        for name in possible_names:
            if shutil.which(name.split()[0]):
                return name
        
        # Check common installation paths
        common_paths = [
            Path.home() / 'DiscordChatExporter',
            Path('/usr/local/bin/DiscordChatExporter.Cli'),
            Path('./tools/DiscordChatExporter.Cli')
        ]
        
        for path in common_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def export_channel(
        self, 
        channel_id: str, 
        output_path: Optional[Path] = None,
        format: str = "Json",
        date_after: Optional[str] = None,
        date_before: Optional[str] = None
    ) -> Path:
        """
        Export a single Discord channel
        
        Args:
            channel_id: Discord channel ID
            output_path: Output file path (if None, creates temp file)
            format: Export format (Json, Csv, Html, etc.)
            date_after: Export messages after this date (YYYY-MM-DD)
            date_before: Export messages before this date (YYYY-MM-DD)
            
        Returns:
            Path to the exported file
        """
        if output_path is None:
            output_path = Path(tempfile.mkdtemp()) / f"channel_{channel_id}.json"
        
        # Build command
        cmd = [
            self.exporter_path,
            "export",
            "-c", channel_id,
            "-t", self.token,
            "-f", format,
            "-o", str(output_path)
        ]
        
        # Add date filters if provided
        if date_after:
            cmd.extend(["--after", date_after])
        if date_before:
            cmd.extend(["--before", date_before])
        
        logger.info(f"Exporting channel {channel_id} to {output_path}")
        
        try:
            # Run the export command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"DiscordChatExporter failed: {result.stderr}")
            
            if not output_path.exists():
                raise FileNotFoundError(f"Expected output file not created: {output_path}")
            
            logger.info(f"Successfully exported channel {channel_id}")
            return output_path
            
        except subprocess.TimeoutExpired:
            logger.error(f"Export timeout for channel {channel_id}")
            raise
        except Exception as e:
            logger.error(f"Failed to export channel {channel_id}: {str(e)}")
            raise
    
    def export_multiple_channels(
        self,
        channel_ids: List[str],
        output_dir: Optional[Path] = None,
        **kwargs
    ) -> List[Path]:
        """
        Export multiple Discord channels
        
        Args:
            channel_ids: List of Discord channel IDs
            output_dir: Output directory (if None, creates temp dir)
            **kwargs: Additional arguments passed to export_channel
            
        Returns:
            List of paths to exported files
        """
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = []
        
        for channel_id in channel_ids:
            try:
                output_path = output_dir / f"channel_{channel_id}.json"
                exported_file = self.export_channel(
                    channel_id, 
                    output_path, 
                    **kwargs
                )
                exported_files.append(exported_file)
                
                # Rate limiting - wait between exports
                import time
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to export channel {channel_id}: {str(e)}")
                continue
        
        logger.info(f"Exported {len(exported_files)} out of {len(channel_ids)} channels")
        return exported_files
    
    def export_guild(
        self,
        guild_id: str,
        output_dir: Optional[Path] = None,
        include_threads: bool = False,
        **kwargs
    ) -> List[Path]:
        """
        Export all channels from a Discord guild/server
        
        Args:
            guild_id: Discord guild ID
            output_dir: Output directory
            include_threads: Whether to include thread channels
            **kwargs: Additional arguments passed to export_channel
            
        Returns:
            List of paths to exported files
        """
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build command to export entire guild
        cmd = [
            self.exporter_path,
            "exportguild",
            "-g", guild_id,
            "-t", self.token,
            "-f", kwargs.get('format', 'Json'),
            "-o", str(output_dir / "guild_{guild}.json")
        ]
        
        if include_threads:
            cmd.append("--include-threads")
        
        # Add date filters if provided
        if kwargs.get('date_after'):
            cmd.extend(["--after", kwargs['date_after']])
        if kwargs.get('date_before'):
            cmd.extend(["--before", kwargs['date_before']])
        
        logger.info(f"Exporting guild {guild_id} to {output_dir}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=7200  # 2 hour timeout for full guild
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Guild export failed: {result.stderr}")
            
            # Find all exported files
            exported_files = list(output_dir.glob("*.json"))
            logger.info(f"Successfully exported {len(exported_files)} files from guild {guild_id}")
            
            return exported_files
            
        except subprocess.TimeoutExpired:
            logger.error(f"Guild export timeout for {guild_id}")
            raise
        except Exception as e:
            logger.error(f"Failed to export guild {guild_id}: {str(e)}")
            raise


class DiscordChatExporterIngestor:
    """High-level ingestion interface using DiscordChatExporter"""
    
    def __init__(self, token: str, exporter_path: Optional[str] = None):
        self.exporter = DiscordChatExporterClient(token, exporter_path)
    
    def ingest_channels(
        self, 
        channel_ids: List[str],
        cleanup: bool = True,
        **export_kwargs
    ) -> List[Dict[str, Any]]:
        """
        Ingest messages from Discord channels using DiscordChatExporter
        
        Args:
            channel_ids: List of Discord channel IDs to export
            cleanup: Whether to delete temporary files after processing
            **export_kwargs: Additional arguments for export
            
        Returns:
            List of normalized message dictionaries
        """
        logger.info(f"Starting ingestion of {len(channel_ids)} channels")
        
        # Export channels to temporary files
        exported_files = self.exporter.export_multiple_channels(
            channel_ids, 
            **export_kwargs
        )
        
        all_messages = []
        
        try:
            # Process each exported file
            for file_path in exported_files:
                messages = self._load_and_normalize_export(file_path)
                all_messages.extend(messages)
                
                logger.info(f"Processed {len(messages)} messages from {file_path.name}")
        
        finally:
            # Cleanup temporary files if requested
            if cleanup:
                for file_path in exported_files:
                    try:
                        file_path.unlink()
                        # Remove parent directory if it's a temp dir and empty
                        if file_path.parent.name.startswith('tmp'):
                            file_path.parent.rmdir()
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {file_path}: {str(e)}")
        
        logger.info(f"Ingested total of {len(all_messages)} messages")
        return all_messages
    
    def ingest_guild(
        self,
        guild_id: str,
        cleanup: bool = True,
        **export_kwargs
    ) -> List[Dict[str, Any]]:
        """
        Ingest messages from entire Discord guild using DiscordChatExporter
        
        Args:
            guild_id: Discord guild ID
            cleanup: Whether to delete temporary files
            **export_kwargs: Additional arguments for export
            
        Returns:
            List of normalized message dictionaries
        """
        logger.info(f"Starting guild ingestion for {guild_id}")
        
        # Export entire guild
        exported_files = self.exporter.export_guild(guild_id, **export_kwargs)
        
        all_messages = []
        
        try:
            # Process each exported file
            for file_path in exported_files:
                messages = self._load_and_normalize_export(file_path)
                all_messages.extend(messages)
                
                logger.info(f"Processed {len(messages)} messages from {file_path.name}")
        
        finally:
            # Cleanup if requested
            if cleanup:
                for file_path in exported_files:
                    try:
                        file_path.unlink()
                        if file_path.parent.name.startswith('tmp'):
                            file_path.parent.rmdir()
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {file_path}: {str(e)}")
        
        logger.info(f"Ingested total of {len(all_messages)} messages from guild")
        return all_messages
    
    def _load_and_normalize_export(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load and normalize a DiscordChatExporter JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # DiscordChatExporter format has messages in 'messages' array
            if 'messages' in data:
                messages = data['messages']
            else:
                messages = data if isinstance(data, list) else []
            
            channel_info = data.get('channel', {})
            
            return self._normalize_messages(messages, channel_info)
            
        except Exception as e:
            logger.error(f"Failed to load export file {file_path}: {str(e)}")
            return []
    
    def _normalize_messages(self, messages: List[Dict], channel_info: Dict) -> List[Dict[str, Any]]:
        """Normalize DiscordChatExporter messages to standard format"""
        normalized = []
        
        for msg in messages:
            try:
                # Skip system messages and messages without content
                if (msg.get('type') not in ['Default', 'Reply'] or 
                    not (msg.get('content') or msg.get('attachments') or msg.get('embeds'))):
                    continue
                
                normalized_msg = {
                    'id': msg.get('id'),
                    'channel_id': channel_info.get('id') or msg.get('channelId'),
                    'channel_name': channel_info.get('name') or msg.get('channelName'),
                    'guild_id': channel_info.get('guild', {}).get('id'),
                    'guild_name': channel_info.get('guild', {}).get('name'),
                    'author_id': msg.get('author', {}).get('id'),
                    'author_name': msg.get('author', {}).get('name'),
                    'author_display_name': msg.get('author', {}).get('displayName'),
                    'author_avatar': msg.get('author', {}).get('avatarUrl'),
                    'content': msg.get('content', ''),
                    'timestamp': msg.get('timestamp'),
                    'edited_timestamp': msg.get('timestampEdited'),
                    'message_type': msg.get('type', 'Default'),
                    'attachments': msg.get('attachments', []),
                    'embeds': msg.get('embeds', []),
                    'reactions': msg.get('reactions', []),
                    'mentions': msg.get('mentions', []),
                    'reply_to': msg.get('reference', {}).get('messageId') if msg.get('reference') else None,
                    'pinned': msg.get('isPinned', False),
                    'raw_data': msg
                }
                
                normalized.append(normalized_msg)
                
            except Exception as e:
                logger.warning(f"Failed to normalize message {msg.get('id', 'unknown')}: {str(e)}")
                continue
        
        return normalized