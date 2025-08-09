#!/usr/bin/env python3
"""
Main pipeline script for Discord Knowledge Graph processing
Supports both GCS exports and local JSON files
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('pipeline.log')
        ]
    )

async def main():
    parser = argparse.ArgumentParser(description="Discord Knowledge Graph Pipeline")
    parser.add_argument('--mode', choices=['gcs', 'local'], default='gcs',
                       help='Data source mode: gcs (Google Cloud Storage) or local (JSON files)')
    parser.add_argument('--gcp-project', help='Google Cloud Project ID')
    parser.add_argument('--gcs-bucket', help='Google Cloud Storage bucket name')
    parser.add_argument('--export-date', help='Specific export date to process (YYYYMMDD_HHMMSS)')
    parser.add_argument('--local-path', help='Path to local JSON files')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info(f"🚀 Starting Discord Knowledge Graph Pipeline in {args.mode} mode")
    
    try:
        # Import here to avoid circular imports and missing dependencies
        from discord_kg.ingestion.discord_client import DiscordIngestor
        
        # Initialize Discord ingestor
        ingestor = DiscordIngestor()
        
        if args.mode == 'gcs':
            # GCS mode - load from Google Cloud Storage
            if not args.gcp_project or not args.gcs_bucket:
                logger.error("GCS mode requires --gcp-project and --gcs-bucket")
                return 1
            
            logger.info(f"Configuring GCS client for project: {args.gcp_project}")
            ingestor.setup_gcs_client(args.gcp_project, args.gcs_bucket)
            
            # Load messages from GCS
            logger.info("Loading messages from Google Cloud Storage...")
            messages = ingestor.load_latest_exports(args.export_date)
            
        elif args.mode == 'local':
            # Local mode - load from local JSON files
            if not args.local_path:
                logger.error("Local mode requires --local-path")
                return 1
            
            local_path = Path(args.local_path)
            if not local_path.exists():
                logger.error(f"Local path does not exist: {local_path}")
                return 1
            
            logger.info(f"Loading messages from local path: {local_path}")
            messages = []
            
            if local_path.is_file() and local_path.suffix == '.json':
                # Single JSON file
                messages = ingestor.load_exported_json(local_path)
            elif local_path.is_dir():
                # Directory of JSON files
                for json_file in local_path.glob('*.json'):
                    if 'manifest.json' in json_file.name:
                        continue  # Skip manifest files
                    file_messages = ingestor.load_exported_json(json_file)
                    messages.extend(file_messages)
            else:
                logger.error(f"Invalid local path: {local_path}")
                return 1
        
        if not messages:
            logger.warning("No messages loaded - pipeline stopping")
            return 0
        
        logger.info(f"📊 Loaded {len(messages)} messages for processing")
        
        # TODO: Process messages through orchestrator when available
        # For now, just log the basic statistics
        channels = set(msg.get('channel_name') for msg in messages)
        authors = set(msg.get('author_name') for msg in messages)
        
        logger.info(f"📈 Processing summary:")
        logger.info(f"  - Channels: {len(channels)}")
        logger.info(f"  - Authors: {len(authors)}")
        logger.info(f"  - Total messages: {len(messages)}")
        
        logger.info(f"✅ Pipeline completed successfully")
        
        return 0
        
    except ImportError as e:
        logger.error(f"❌ Missing dependencies: {str(e)}")
        logger.info("Install required packages: pip install google-cloud-storage")
        return 1
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))