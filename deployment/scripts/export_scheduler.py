#!/usr/bin/env python3
"""
Scheduler for Discord exports and uploads
"""

import schedule
import time
import subprocess
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/config/.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_export():
    """Run the Discord export process"""
    try:
        logger.info("🚀 Starting scheduled Discord export")
        
        # Run the export script
        result = subprocess.run(
            ['/bin/bash', '/app/scripts/export_discord.sh'],
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            logger.info("✅ Discord export completed successfully")
            
            # Run the uploader
            logger.info("📤 Starting upload to Google Cloud Storage")
            upload_result = subprocess.run(
                ['python', '/app/uploader.py'],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if upload_result.returncode == 0:
                logger.info("✅ Upload completed successfully")
            else:
                logger.error(f"❌ Upload failed: {upload_result.stderr}")
                
        else:
            logger.error(f"❌ Discord export failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Export process timed out")
    except Exception as e:
        logger.error(f"❌ Export process failed: {str(e)}")

def run_health_check():
    """Run system health check"""
    logger.info("🔍 Running health check")
    
    # Check disk space
    disk_usage = subprocess.run(
        ['df', '-h', '/app/exports'],
        capture_output=True,
        text=True
    )
    logger.info(f"Disk usage: {disk_usage.stdout}")
    
    # Check Docker containers
    docker_ps = subprocess.run(
        ['docker', 'ps'],
        capture_output=True,
        text=True
    )
    logger.info(f"Docker containers: {docker_ps.stdout}")

def main():
    """Main scheduler function"""
    logger.info("🕐 Discord Export Scheduler starting")
    
    # Get schedule from environment (default: daily at 2 AM)
    export_schedule = os.getenv('EXPORT_SCHEDULE', '02:00')
    
    # Schedule the export job
    schedule.every().day.at(export_schedule).do(run_export)
    
    # Schedule health check (every 6 hours)
    schedule.every(6).hours.do(run_health_check)
    
    logger.info(f"📅 Scheduled daily export at {export_schedule}")
    logger.info("🔍 Scheduled health check every 6 hours")
    
    # Run initial health check
    run_health_check()
    
    # Keep the scheduler running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("👋 Scheduler shutting down")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {str(e)}")
            time.sleep(300)  # Wait 5 minutes before retry

if __name__ == '__main__':
    main()