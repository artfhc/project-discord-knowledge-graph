# DiscordChatExporter Integration Guide

Complete guide for integrating [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) with your Discord Knowledge Graph pipeline.

## 🚀 Quick Start

### Option 1: Local Workflow (Recommended for Testing)

```bash
# 1. Install DiscordChatExporter
# Download from: https://github.com/Tyrrrz/DiscordChatExporter/releases

# 2. Export and process specific channels
python scripts/local_discord_export.py \
  --token YOUR_DISCORD_TOKEN \
  --channels 123456789 987654321 \
  --output-dir ./exports \
  --keep-exports

# 3. Export entire server
python scripts/local_discord_export.py \
  --token YOUR_DISCORD_TOKEN \
  --guild SERVER_ID \
  --date-after 2024-01-01
```

### Option 2: Cloud Workflow (Production)

```bash
# 1. Deploy to Google Cloud (see deployment/ folder)
./deployment/gcp-vm-create.sh

# 2. Configure and run automated exports
# (Files automatically processed and stored in GCS)

# 3. Process from your local environment
python scripts/run_pipeline.py \
  --mode gcs \
  --gcp-project YOUR_PROJECT \
  --gcs-bucket discord-exports
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ DiscordChat     │────│ Integration      │────│ Knowledge Graph │
│ Exporter        │    │ Layer            │    │ Pipeline        │
│                 │    │                  │    │                 │
│ • JSON Export   │────│ • Normalization  │────│ • Classification│
│ • Rate Limited  │    │ • Validation     │    │ • Extraction    │
│ • Rich Metadata │    │ • Format Conv.   │    │ • Storage       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📚 Integration Methods

### 1. Direct Integration

```python
from discord_kg.ingestion.discord_chat_exporter import DiscordChatExporterIngestor

# Initialize with your token
ingestor = DiscordChatExporterIngestor("YOUR_DISCORD_TOKEN")

# Export specific channels
messages = ingestor.ingest_channels(["123456789", "987654321"])

# Export entire server
messages = ingestor.ingest_guild("SERVER_ID")
```

### 2. Orchestrator Integration

```python
from discord_kg.ingestion.orchestrator import IngestionOrchestrator

orchestrator = IngestionOrchestrator()

# Export and process in one step
messages = orchestrator.ingest_from_discord_chat_exporter(
    discord_token="YOUR_TOKEN",
    channel_ids=["123456789"],
    date_after="2024-01-01"
)

# Process through complete pipeline
results = orchestrator.process_messages(messages)
```

### 3. Local Files Processing

```python
# Process existing exported files
messages = orchestrator.ingest_from_local_files([
    Path("channel_123.json"),
    Path("channel_456.json")
])
```

### 4. Cloud Storage Integration

```python
# Process from Google Cloud Storage
messages = orchestrator.ingest_from_gcs(
    gcp_project="your-project",
    bucket_name="discord-exports"
)
```

## 🔧 Configuration Options

### Export Configuration

```python
export_kwargs = {
    'date_after': '2024-01-01',      # Start date filter
    'date_before': '2024-12-31',     # End date filter
    'format': 'Json',                # Export format
    'cleanup': True,                 # Delete temp files
    'include_threads': True          # Include thread messages
}
```

### Processing Configuration

```python
config = {
    'storage': {
        'type': 'b2',
        'key_id': 'your_key',
        'application_key': 'your_app_key',
        'bucket_name': 'discord-data'
    }
}

orchestrator = IngestionOrchestrator(config)
```

## 🛠️ Setup Requirements

### 1. DiscordChatExporter Installation

**Option A: Direct Download**
```bash
# Download from GitHub releases
wget https://github.com/Tyrrrz/DiscordChatExporter/releases/download/2.42.4/DiscordChatExporter.Cli.linux-x64.zip
unzip DiscordChatExporter.Cli.linux-x64.zip
chmod +x DiscordChatExporter.Cli
```

**Option B: Docker**
```bash
docker pull tyrrrz/discordchatexporter:stable
```

**Option C: Package Manager**
```bash
# Arch Linux
yay -S discord-chat-exporter-cli

# Nix
nix-shell -p discordchatexporter-cli
```

### 2. Discord Token Setup

**User Token (Personal Use)**
1. Open Discord in browser
2. Press F12 → Network tab
3. Send any message
4. Find request with Authorization header
5. Copy token (without "Bearer ")

**Bot Token (Server Use)**
1. Go to Discord Developer Portal
2. Create application → Bot
3. Copy bot token
4. Invite bot to server with required permissions

### 3. Python Dependencies

```bash
pip install google-cloud-storage  # For GCS integration
```

## 📊 Data Format

### DiscordChatExporter Output
```json
{
  "guild": {"id": "123", "name": "Server Name"},
  "channel": {"id": "456", "name": "general"},
  "messages": [
    {
      "id": "789",
      "timestamp": "2024-01-01T12:00:00+00:00",
      "author": {
        "id": "999",
        "name": "username",
        "displayName": "Display Name"
      },
      "content": "Message content here",
      "attachments": [],
      "embeds": [],
      "reactions": []
    }
  ]
}
```

### Normalized Internal Format
```json
{
  "id": "789",
  "channel_id": "456",
  "channel_name": "general",
  "guild_id": "123",
  "guild_name": "Server Name",
  "author_id": "999",
  "author_name": "username",
  "author_display_name": "Display Name",
  "content": "Message content here",
  "timestamp": "2024-01-01T12:00:00+00:00",
  "message_type": "Default",
  "attachments": [],
  "embeds": [],
  "reactions": [],
  "reply_to": null,
  "raw_data": {...}
}
```

## 🔄 Processing Pipeline

1. **Export** → DiscordChatExporter creates JSON files
2. **Normalize** → Convert to internal format
3. **Clean** → Remove system messages, filter content
4. **Classify** → Categorize as question/answer/alert/strategy
5. **Extract** → Generate knowledge graph triples
6. **Store** → Save to database/file system

## ⚡ Performance Tips

### Rate Limiting
- DiscordChatExporter handles Discord rate limits automatically
- For multiple channels, add delays between exports
- Use date ranges to limit data volume

### Memory Management
```python
# Process in batches for large exports
ingestor = DiscordChatExporterIngestor(token, cleanup=True)
messages = ingestor.ingest_channels(channel_ids, cleanup=True)
```

### Storage Optimization
```python
# Use date-based filtering
messages = ingestor.ingest_channels(
    channel_ids,
    date_after="2024-01-01",
    date_before="2024-01-31"
)
```

## 🚨 Error Handling

### Common Issues

**1. Missing DiscordChatExporter**
```
ValueError: DiscordChatExporter.Cli not found
```
Solution: Install DiscordChatExporter and ensure it's in PATH

**2. Invalid Token**
```
RuntimeError: DiscordChatExporter failed: Unauthorized
```
Solution: Check token validity and permissions

**3. Channel Access**
```
RuntimeError: DiscordChatExporter failed: Forbidden
```
Solution: Ensure bot/user has read permissions for channels

**4. Rate Limited**
```
RuntimeError: Rate limit exceeded
```
Solution: DiscordChatExporter handles this automatically, but reduce concurrency

### Error Recovery

```python
try:
    messages = ingestor.ingest_channels(channel_ids)
except Exception as e:
    logger.error(f"Export failed: {e}")
    # Fallback to individual channel export
    messages = []
    for channel_id in channel_ids:
        try:
            channel_messages = ingestor.ingest_channels([channel_id])
            messages.extend(channel_messages)
        except Exception as channel_error:
            logger.error(f"Failed to export {channel_id}: {channel_error}")
```

## 🔒 Security Best Practices

### Token Management
```bash
# Store token in environment variable
export DISCORD_TOKEN="your_token_here"

# Use in scripts
python scripts/local_discord_export.py --token "$DISCORD_TOKEN"
```

### File Permissions
```bash
# Restrict access to exported files
chmod 600 exports/*.json

# Use temporary directories for processing
python scripts/local_discord_export.py --token "$DISCORD_TOKEN" --cleanup
```

## 📈 Monitoring & Logging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or in scripts
python scripts/local_discord_export.py --log-level DEBUG
```

### Track Processing Metrics
```python
results = orchestrator.process_messages(messages)
metrics = results['summary']

print(f"Processed: {metrics['classified_messages']} messages")
print(f"Extracted: {metrics['extracted_triples']} triples")
```

## 🤝 Integration Examples

See `examples/sample_usage.py` for complete working examples of all integration methods.

## 📞 Support

- **DiscordChatExporter Issues**: https://github.com/Tyrrrz/DiscordChatExporter/issues
- **Pipeline Issues**: Check logs and error messages
- **Discord API Limits**: https://discord.com/developers/docs/topics/rate-limits