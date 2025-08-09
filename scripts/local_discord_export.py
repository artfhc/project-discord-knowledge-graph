#!/usr/bin/env python3
"""
Local Discord export and processing workflow using DiscordChatExporter
No cloud dependencies - works entirely locally
"""

import argparse
import logging
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('discord_export.log')
        ]
    )

def main():
    parser = argparse.ArgumentParser(description="Local Discord Export and Processing")
    parser.add_argument('--token', help='Discord token (user or bot)')
    parser.add_argument('--exporter-path', help='Path to DiscordChatExporter.Cli executable')
    
    # Export options
    export_group = parser.add_mutually_exclusive_group()
    export_group.add_argument('--channels', nargs='+', help='Discord channel IDs to export')
    export_group.add_argument('--guild', help='Discord guild/server ID to export entirely')
    export_group.add_argument('--process-only', help='Process existing exported files from directory')
    
    # Processing options
    parser.add_argument('--output-dir', help='Directory to save exported files (default: temp dir)')
    parser.add_argument('--keep-exports', action='store_true', 
                       help='Keep exported JSON files after processing')
    parser.add_argument('--export-only', action='store_true',
                       help='Only export, do not process through pipeline')
    
    # Export filters
    parser.add_argument('--date-after', help='Export messages after date (YYYY-MM-DD)')
    parser.add_argument('--date-before', help='Export messages before date (YYYY-MM-DD)')
    
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.process_only:
        # Process-only mode doesn't need token or export options
        pass
    else:
        # Export mode requires token and either channels or guild
        if not args.token:
            parser.error("--token is required when exporting (not needed for --process-only)")
        if not args.channels and not args.guild:
            parser.error("Either --channels or --guild is required when exporting")
    
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        if args.process_only:
            # Process existing exported files
            logger.info("🔄 Processing existing exported files")
            return process_existing_files(args.process_only, logger)
        
        # Import here to check dependencies
        from discord_kg.ingestion.orchestrator import IngestionOrchestrator
        
        # Initialize orchestrator
        orchestrator = IngestionOrchestrator()
        
        # Determine output directory
        if args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = None  # Will use temp directory
        
        # Prepare export arguments
        export_kwargs = {
            'output_dir': output_dir,
            'cleanup': not args.keep_exports,
        }
        
        if args.date_after:
            export_kwargs['date_after'] = args.date_after
        if args.date_before:
            export_kwargs['date_before'] = args.date_before
        
        # Perform export
        if args.guild:
            logger.info(f"🚀 Exporting entire guild: {args.guild}")
            messages = orchestrator.ingest_from_discord_chat_exporter(
                discord_token=args.token,
                guild_id=args.guild,
                exporter_path=args.exporter_path,
                **export_kwargs
            )
        else:
            logger.info(f"🚀 Exporting {len(args.channels)} channels")
            messages = orchestrator.ingest_from_discord_chat_exporter(
                discord_token=args.token,
                channel_ids=args.channels,
                exporter_path=args.exporter_path,
                **export_kwargs
            )
        
        if not messages:
            logger.warning("No messages exported")
            return 0
        
        # Log basic statistics
        channels = set(msg.get('channel_name') for msg in messages)
        authors = set(msg.get('author_name') for msg in messages)
        
        logger.info(f"📊 Export Summary:")
        logger.info(f"  - Total messages: {len(messages)}")
        logger.info(f"  - Channels: {len(channels)}")
        logger.info(f"  - Authors: {len(authors)}")
        
        if args.export_only:
            logger.info("✅ Export completed (processing skipped)")
            return 0
        
        # Process through pipeline
        logger.info("🔄 Processing messages through knowledge graph pipeline")
        results = orchestrator.process_messages(messages)
        
        # Log processing results
        summary = results['summary']
        logger.info(f"📈 Processing Summary:")
        logger.info(f"  - Input messages: {summary['input_messages']}")
        logger.info(f"  - Cleaned messages: {summary['cleaned_messages']}")
        logger.info(f"  - Classified messages: {summary['classified_messages']}")
        logger.info(f"  - Extracted triples: {summary['extracted_triples']}")
        
        # Save results if output directory specified
        if args.output_dir and args.keep_exports:
            results_file = Path(args.output_dir) / 'processing_results.json'
            import json
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"💾 Results saved to: {results_file}")
        
        logger.info("✅ Pipeline completed successfully")
        return 0
        
    except ImportError as e:
        logger.error(f"❌ Missing dependencies: {str(e)}")
        logger.info("Install DiscordChatExporter and ensure it's in your PATH")
        return 1
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {str(e)}", exc_info=True)
        return 1

def process_existing_files(directory: str, logger) -> int:
    """Process existing exported JSON files using simplified processing"""
    try:
        import json
        from discord_kg.ingestion.discord_client import DiscordIngestor
        
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            return 1
        
        # Find JSON files
        json_files = list(dir_path.glob('*.json'))
        if not json_files:
            logger.error(f"No JSON files found in: {directory}")
            return 1
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        # Load messages using the basic ingestor (no orchestrator dependencies)
        ingestor = DiscordIngestor()
        all_messages = []
        
        for json_file in json_files:
            if 'manifest.json' in json_file.name:
                continue  # Skip manifest files
                
            messages = ingestor.load_exported_json(json_file)
            all_messages.extend(messages)
            logger.info(f"Loaded {len(messages)} messages from {json_file.name}")
        
        if not all_messages:
            logger.warning("No messages loaded from files")
            return 0
        
        logger.info(f"📊 Total loaded messages: {len(all_messages)}")
        
        # Simple processing without full pipeline dependencies
        channels = set(msg.get('channel_name') for msg in all_messages if msg.get('channel_name'))
        authors = set(msg.get('author_name') for msg in all_messages if msg.get('author_name'))
        content_messages = [msg for msg in all_messages if msg.get('content')]
        
        # Basic content analysis
        total_chars = sum(len(msg.get('content', '')) for msg in content_messages)
        avg_message_length = total_chars / len(content_messages) if content_messages else 0
        
        # Simple "knowledge" indicators
        question_indicators = ['?', 'how', 'what', 'why', 'when', 'where', 'who']
        potential_questions = []
        
        for msg in content_messages:
            content_lower = msg.get('content', '').lower()
            if any(indicator in content_lower for indicator in question_indicators):
                potential_questions.append(msg)
        
        # Create results summary
        results = {
            'summary': {
                'total_messages': len(all_messages),
                'content_messages': len(content_messages),
                'channels': len(channels),
                'authors': len(authors),
                'potential_questions': len(potential_questions),
                'avg_message_length': round(avg_message_length, 2),
                'total_characters': total_chars
            },
            'channels_list': list(channels),
            'authors_list': list(authors),
            'sample_questions': potential_questions[:5]  # First 5 questions
        }
        
        # Log results
        summary = results['summary']
        logger.info(f"📈 Processing Summary:")
        logger.info(f"  - Total messages: {summary['total_messages']}")
        logger.info(f"  - Content messages: {summary['content_messages']}")
        logger.info(f"  - Channels: {summary['channels']}")
        logger.info(f"  - Authors: {summary['authors']}")
        logger.info(f"  - Potential questions: {summary['potential_questions']}")
        logger.info(f"  - Avg message length: {summary['avg_message_length']} chars")
        
        # Save results
        results_file = dir_path / 'processing_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved to: {results_file}")
        logger.info("✅ Processing completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())