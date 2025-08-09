#!/usr/bin/env python3
"""
Sample usage examples for DiscordChatExporter integration
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def example_direct_integration():
    """Example: Direct DiscordChatExporter integration"""
    from discord_kg.ingestion.discord_chat_exporter import DiscordChatExporterIngestor
    
    # Initialize with your Discord token
    discord_token = "YOUR_DISCORD_TOKEN_HERE"
    exporter_path = "/path/to/DiscordChatExporter.Cli"  # Optional
    
    ingestor = DiscordChatExporterIngestor(discord_token, exporter_path)
    
    # Export specific channels
    channel_ids = ["123456789", "987654321"]
    messages = ingestor.ingest_channels(channel_ids)
    
    print(f"Ingested {len(messages)} messages from {len(channel_ids)} channels")
    
    # Or export entire server
    guild_id = "SERVER_ID_HERE"
    all_messages = ingestor.ingest_guild(guild_id)
    
    print(f"Ingested {len(all_messages)} messages from entire guild")

def example_orchestrator_usage():
    """Example: Using the orchestrator for complete pipeline"""
    from discord_kg.ingestion.orchestrator import IngestionOrchestrator
    
    # Initialize orchestrator
    orchestrator = IngestionOrchestrator()
    
    # Method 1: Export and process in one step
    discord_token = "YOUR_DISCORD_TOKEN_HERE"
    channel_ids = ["123456789", "987654321"]
    
    messages = orchestrator.ingest_from_discord_chat_exporter(
        discord_token=discord_token,
        channel_ids=channel_ids,
        date_after="2024-01-01",  # Optional date filter
        cleanup=True  # Remove temp files after processing
    )
    
    # Process through complete pipeline
    results = orchestrator.process_messages(messages)
    
    print("Processing Results:")
    print(f"- Messages: {results['summary']['classified_messages']}")
    print(f"- Triples: {results['summary']['extracted_triples']}")

def example_local_files():
    """Example: Processing existing exported files"""
    from discord_kg.ingestion.orchestrator import IngestionOrchestrator
    
    orchestrator = IngestionOrchestrator()
    
    # Process existing JSON files
    json_files = [
        Path("exports/channel_123456789.json"),
        Path("exports/channel_987654321.json")
    ]
    
    messages = orchestrator.ingest_from_local_files(json_files)
    results = orchestrator.process_messages(messages)
    
    print(f"Processed {len(messages)} messages from {len(json_files)} files")

def example_gcs_integration():
    """Example: Processing files from Google Cloud Storage"""
    from discord_kg.ingestion.orchestrator import IngestionOrchestrator
    
    orchestrator = IngestionOrchestrator()
    
    # Load from GCS
    messages = orchestrator.ingest_from_gcs(
        gcp_project="your-gcp-project",
        bucket_name="discord-exports-bucket",
        export_date="20240109_020000"  # Optional specific date
    )
    
    results = orchestrator.process_messages(messages)
    print(f"Processed {len(messages)} messages from GCS")

if __name__ == "__main__":
    print("Discord Knowledge Graph - Usage Examples")
    print("="*50)
    
    print("\n1. Direct DiscordChatExporter Integration:")
    print("   # Export specific channels or entire server")
    print("   python -c 'from examples.sample_usage import example_direct_integration; example_direct_integration()'")
    
    print("\n2. Complete Pipeline with Orchestrator:")
    print("   # Export and process in one step")
    print("   python -c 'from examples.sample_usage import example_orchestrator_usage; example_orchestrator_usage()'")
    
    print("\n3. Process Existing Files:")
    print("   # Process already exported JSON files")
    print("   python -c 'from examples.sample_usage import example_local_files; example_local_files()'")
    
    print("\n4. Google Cloud Storage Integration:")
    print("   # Process files from GCS")
    print("   python -c 'from examples.sample_usage import example_gcs_integration; example_gcs_integration()'")
    
    print("\n5. Command Line Tools:")
    print("   # Local export and processing")
    print("   python scripts/local_discord_export.py --token YOUR_TOKEN --channels 123456789 987654321")
    
    print("   # Process existing files")
    print("   python scripts/local_discord_export.py --process-only /path/to/exported/files/")
    
    print("   # Complete pipeline from GCS")
    print("   python scripts/run_pipeline.py --mode gcs --gcp-project PROJECT --gcs-bucket BUCKET")
    
    print("\nNote: Replace YOUR_TOKEN, channel IDs, and paths with your actual values")