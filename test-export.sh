#!/bin/bash
# Test Discord export with a single channel

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 CHANNEL_ID [CHANNEL_NAME]"
    echo "Example: $0 123456789012345678 general"
    exit 1
fi

CHANNEL_ID="$1"
CHANNEL_NAME="${2:-test_channel}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "🔄 Testing Discord export for channel: $CHANNEL_ID"

# Ensure containers are running
docker-compose -f docker-compose.local.yml up -d

# Run export
echo "📥 Exporting channel $CHANNEL_ID..."
docker run --rm \
    -v "$(pwd)/exports:/out" \
    -v "$(pwd)/config:/config:ro" \
    tyrrrz/discordchatexporter:stable \
    export \
    -t "$(cat config/discord_token)" \
    -c "$CHANNEL_ID" \
    -f Json \
    -o "/out/${CHANNEL_NAME}_${CHANNEL_ID}_${TIMESTAMP}.json"

# Check if export was successful
EXPORT_FILE="exports/${CHANNEL_NAME}_${CHANNEL_ID}_${TIMESTAMP}.json"

if [ -f "$EXPORT_FILE" ]; then
    echo "✅ Export successful! File: $EXPORT_FILE"
    
    # Show basic stats
    echo "📊 Export stats:"
    echo "  File size: $(du -h "$EXPORT_FILE" | cut -f1)"
    
    # Try to get message count (requires jq)
    if command -v jq &> /dev/null; then
        MESSAGE_COUNT=$(jq '.messages | length' "$EXPORT_FILE" 2>/dev/null || echo "unknown")
        echo "  Messages: $MESSAGE_COUNT"
    fi
    
    echo ""
    echo "🔄 Testing pipeline processing..."
    
    # Test processing with the pipeline
    docker-compose -f docker-compose.local.yml exec pipeline-processor \
        python scripts/local_discord_export.py \
        --process-only /app/exports \
        --log-level INFO
    
else
    echo "❌ Export failed - file not found: $EXPORT_FILE"
    echo "Check Docker logs:"
    docker-compose -f docker-compose.local.yml logs discord-exporter-local
    exit 1
fi

echo ""
echo "🎉 Test completed successfully!"
echo "Export file: $EXPORT_FILE"
echo "View logs: docker-compose -f docker-compose.local.yml logs"