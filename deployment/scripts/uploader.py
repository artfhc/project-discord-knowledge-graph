#!/usr/bin/env python3
"""
Google Cloud Storage uploader for Discord exports
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from google.cloud import storage
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/config/.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/uploader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DiscordExportUploader:
    def __init__(self):
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        self.bucket_name = os.getenv('GOOGLE_CLOUD_BUCKET')
        self.export_path = Path('/app/exports')
        
        # Initialize GCS client
        self.client = storage.Client(project=self.project_id)
        self.bucket = self.client.bucket(self.bucket_name)
        
    def upload_export_batch(self, export_dir: Path) -> bool:
        """Upload an entire export batch to GCS"""
        try:
            export_timestamp = export_dir.name
            logger.info(f"Uploading export batch: {export_timestamp}")
            
            # Upload all JSON files in the export directory
            for json_file in export_dir.glob('*.json'):
                blob_path = f"discord-exports/{export_timestamp}/{json_file.name}"
                blob = self.bucket.blob(blob_path)
                
                logger.info(f"Uploading {json_file.name} to {blob_path}")
                blob.upload_from_filename(str(json_file))
                
                # Set metadata
                blob.metadata = {
                    'export_timestamp': export_timestamp,
                    'file_type': 'discord_export',
                    'upload_date': datetime.utcnow().isoformat()
                }
                blob.patch()
                
            logger.info(f"✅ Successfully uploaded export batch: {export_timestamp}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload export batch {export_dir}: {str(e)}")
            return False
    
    def cleanup_local_exports(self, export_dir: Path, keep_local: bool = False):
        """Clean up local export files after successful upload"""
        if not keep_local:
            try:
                for file in export_dir.glob('*'):
                    file.unlink()
                export_dir.rmdir()
                logger.info(f"🧹 Cleaned up local files: {export_dir}")
            except Exception as e:
                logger.error(f"Failed to cleanup {export_dir}: {str(e)}")
    
    def process_pending_exports(self):
        """Process all pending export directories"""
        if not self.export_path.exists():
            logger.warning("Export directory does not exist")
            return
            
        # Find all export directories (timestamped folders)
        export_dirs = [d for d in self.export_path.iterdir() 
                      if d.is_dir() and d.name.replace('_', '').isdigit()]
        
        if not export_dirs:
            logger.info("No pending exports found")
            return
            
        logger.info(f"Found {len(export_dirs)} pending export(s)")
        
        for export_dir in sorted(export_dirs):
            success = self.upload_export_batch(export_dir)
            if success:
                self.cleanup_local_exports(export_dir, keep_local=False)
    
    def get_upload_status(self) -> Dict:
        """Get upload statistics"""
        try:
            blobs = list(self.bucket.list_blobs(prefix='discord-exports/'))
            
            status = {
                'total_files': len(blobs),
                'total_size_mb': sum(blob.size for blob in blobs) / (1024 * 1024),
                'last_upload': max((blob.time_created for blob in blobs), default=None),
                'bucket_name': self.bucket_name
            }
            
            return status
        except Exception as e:
            logger.error(f"Failed to get upload status: {str(e)}")
            return {}

def main():
    """Main uploader function"""
    logger.info("🚀 Starting Discord export uploader")
    
    uploader = DiscordExportUploader()
    uploader.process_pending_exports()
    
    # Log status
    status = uploader.get_upload_status()
    if status:
        logger.info(f"📊 Upload Status: {json.dumps(status, indent=2, default=str)}")
    
    logger.info("✅ Upload process completed")

if __name__ == '__main__':
    main()