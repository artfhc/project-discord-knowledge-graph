#!/usr/bin/env python3
"""Main pipeline execution script"""

import asyncio
import click
from src.discord_kg.utils.config import settings
from src.discord_kg.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)

@click.command()
@click.option('--full', is_flag=True, help='Run full pipeline (ingestion + preprocessing + extraction)')
@click.option('--ingest-only', is_flag=True, help='Run ingestion only')
@click.option('--process-only', is_flag=True, help='Run preprocessing + extraction only')
async def main(full: bool, ingest_only: bool, process_only: bool):
    """Main pipeline execution"""
    configure_logging(settings.log_level)
    
    logger.info("Starting Discord KG Pipeline")
    
    if full or ingest_only:
        logger.info("Running ingestion phase")
        # TODO: Initialize and run ingestion
    
    if full or process_only:
        logger.info("Running preprocessing phase")
        # TODO: Initialize and run preprocessing
        
        logger.info("Running extraction phase")  
        # TODO: Initialize and run extraction
    
    logger.info("Pipeline completed")

if __name__ == "__main__":
    asyncio.run(main())