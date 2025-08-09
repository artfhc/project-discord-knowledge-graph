# Local Docker Testing Guide

Quick guide to test DiscordChatExporter integration locally with Docker.

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Run the setup script
./test-local.sh
```

This creates:
- `exports/` - Directory for exported JSON files
- `config/` - Configuration directory
- `logs/` - Log files

### 2. Configure Discord Token
```bash
# Add your Discord token
echo 'YOUR_DISCORD_TOKEN_HERE' > config/discord_token
chmod 600 config/discord_token
```

### 3. Test Single Channel Export
```bash
# Test with a channel ID (replace with real ID)
./test-export.sh 123456789012345678 general
```

### 4. View Results
```bash
# Check exported files
ls -la exports/

# View processing logs
docker-compose -f docker-compose.local.yml logs pipeline-processor
```

## 🛠️ Manual Testing

### Manual Export Commands
```bash
# Direct docker run (recommended)
docker run --rm \
  -v "$(pwd)/exports:/out" \
  -v "$(pwd)/config:/config:ro" \
  tyrrrz/discordchatexporter:stable \
  export \
  -t "$(cat config/discord_token)" \
  -c CHANNEL_ID \
  -f Json \
  -o "/out/test_export.json"
```

### Pipeline Processing Container
```bash
# Access the Python processing container
docker-compose -f docker-compose.local.yml exec pipeline-processor bash

# Run pipeline on exported files
python scripts/local_discord_export.py --process-only /app/exports
```

## 🔧 Configuration Options

### Export Multiple Channels
```bash
# Edit config/channels.txt with your channel IDs
# Format: CHANNEL_ID,CHANNEL_NAME
123456789012345678,general
234567890123456789,trading-signals
```

Then run batch export:
```bash
while IFS="," read -r CHANNEL_ID CHANNEL_NAME; do
  [[ "$CHANNEL_ID" =~ ^#.*$ ]] && continue
  [[ -z "$CHANNEL_ID" ]] && continue
  
  echo "Exporting $CHANNEL_NAME ($CHANNEL_ID)..."
  docker run --rm \
    -v "$(pwd)/exports:/out" \
    -v "$(pwd)/config:/config:ro" \
    tyrrrz/discordchatexporter:stable \
    export \
    -t "$(cat config/discord_token)" \
    -c "$CHANNEL_ID" \
    -f Json \
    -o "/out/${CHANNEL_NAME}_${CHANNEL_ID}.json"
done < config/channels.txt
```

### Date Filtering
```bash
# Export only recent messages (last 30 days)
docker run --rm \
  -v "$(pwd)/exports:/out" \
  -v "$(pwd)/config:/config:ro" \
  tyrrrz/discordchatexporter:stable \
  export \
  -t "$(cat config/discord_token)" \
  -c CHANNEL_ID \
  -f Json \
  --after $(date -d '30 days ago' +%Y-%m-%d) \
  -o "/out/recent_messages.json"
```

## 🐛 Troubleshooting

### Common Issues

**1. Permission Denied**
```bash
# Fix file permissions
sudo chown -R $USER:$USER exports/ config/ logs/
chmod 600 config/discord_token
```

**2. Container Not Starting**
```bash
# Check container status
docker-compose -f docker-compose.local.yml ps

# View logs
docker-compose -f docker-compose.local.yml logs
```

**3. Invalid Discord Token**
```bash
# Test token manually
docker run --rm tyrrrz/discordchatexporter:stable --version
```

**4. Channel Access Denied**
- Ensure your Discord account/bot has access to the channel
- Check if the server allows message history access
- Verify the channel ID is correct (enable Developer Mode in Discord)

### Getting Channel IDs
1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click on any channel
3. Select "Copy ID"

## 📊 Testing Results

After running `./test-export.sh`, you should see:

```
✅ Export successful! File: exports/general_123456789_20240109_143022.json
📊 Export stats:
  File size: 2.3M
  Messages: 1547

🔄 Testing pipeline processing...
📊 Loaded 1547 messages from 1 files
📈 Processing Summary:
  - Extracted triples: 234

🎉 Test completed successfully!
```

## 🧹 Cleanup

```bash
# Stop containers
docker-compose -f docker-compose.local.yml down

# Remove test data (optional)
rm -rf exports/* logs/*

# Remove Docker images (optional)
docker rmi tyrrrz/discordchatexporter:stable
```

## 🔄 Development Workflow

1. **Test Export** → `./test-export.sh CHANNEL_ID`
2. **Check Results** → `ls exports/`
3. **Debug Issues** → `docker-compose logs`
4. **Iterate** → Modify code and retest

This local setup gives you a complete testing environment without needing cloud resources!