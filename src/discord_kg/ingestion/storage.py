"""Storage handlers for raw Discord data"""

import json
from typing import List, Dict, Any
from datetime import datetime

class B2Storage:
    """Handles storage of raw messages to Backblaze B2"""
    
    def __init__(self, key_id: str, application_key: str, bucket_name: str):
        self.key_id = key_id
        self.application_key = application_key
        self.bucket_name = bucket_name
    
    def store_messages(self, messages: List[Dict[str, Any]], server_id: int, channel_id: int) -> str:
        """Store messages in partitioned structure"""
        # TODO: Implement B2 storage
        # - Create partitioned path structure
        # - Upload JSON files to B2
        # - Return storage path/key
        pass
    
    def get_partition_key(self, server_id: int, channel_id: int, date: datetime) -> str:
        """Generate partition key for message storage"""
        # TODO: Generate S3-style partition keys
        # Format: server_id=123/channel_id=456/year=2024/month=01/day=15/
        pass