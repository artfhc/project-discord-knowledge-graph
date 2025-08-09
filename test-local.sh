#!/bin/bash
# Local Docker testing script for Discord Knowledge Graph

set -e

echo "🚀 Setting up local Discord export test environment..."

# Create required directories
mkdir -p exports config logs

# Check if Discord token exists
if [ ! -f "config/discord_token" ]; then
    echo "⚠️  Discord token not found!"
    echo "Please create config/discord_token with your Discord token:"
    echo "  echo 'YOUR_DISCORD_TOKEN' > config/discord_token"
    echo "  chmod 600 config/discord_token"
    exit 1
fi

# Create channels configuration if it doesn't exist
if [ ! -f "config/channels.txt" ]; then
    echo "📝 Creating sample channels.txt..."
    cat > config/channels.txt << 'EOF'
# Discord Channels Configuration
# Format: CHANNEL_ID,CHANNEL_NAME
# Replace with your actual channel IDs

# Example (replace with real channel IDs):
123456789012345678,general
234567890123456789,random
EOF
    echo "⚠️  Please edit config/channels.txt with your actual channel IDs"
fi

echo "🐳 Starting Docker containers..."
docker-compose -f docker-compose.local.yml up -d

echo "⏳ Waiting for containers to start..."
sleep 5

echo "✅ Local test environment ready!"
echo ""
echo "Next steps:"
echo "1. Edit config/channels.txt with your actual Discord channel IDs"
echo "2. Test export with: ./test-export.sh CHANNEL_ID"
echo "3. Or run interactive test: docker-compose -f docker-compose.local.yml exec discord-exporter-local bash"
echo ""
echo "To stop: docker-compose -f docker-compose.local.yml down"