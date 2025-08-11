#!/bin/bash
# Discord Channel Export Script
set -e

# Load environment variables
source /app/config/.env

# Configuration
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
EXPORT_DIR="/app/exports/$TIMESTAMP"

# Create export directory
mkdir -p "$EXPORT_DIR"

# Function to export a channel
export_channel() {
    local CHANNEL_ID="$1"
    local CHANNEL_NAME="$2"
    
    echo "📥 Exporting channel: $CHANNEL_NAME ($CHANNEL_ID)"
    
    docker run --rm \
        -v "$(pwd)/exports:/app/exports" \
        -v "$(pwd)/config:/app/config:ro" \
        tyrrrz/discordchatexporter:stable \
        export \
        -t "$DISCORD_TOKEN" \
        -c "$CHANNEL_ID" \
        -f "Json" \
        -o "/app/exports/$TIMESTAMP/${CHANNEL_NAME}_${CHANNEL_ID}.json" \
        --dateformat "yyyy-MM-dd HH:mm:ss"
        
    if [ $? -eq 0 ]; then
        echo "✅ Successfully exported $CHANNEL_NAME"
    else
        echo "❌ Failed to export $CHANNEL_NAME"
        return 1
    fi
}

# Read channels from config file
if [ -f "/app/config/channels.txt" ]; then
    echo "🚀 Starting Discord export process..."
    
    while IFS=',' read -r CHANNEL_ID CHANNEL_NAME; do
        # Skip comments and empty lines
        [[ "$CHANNEL_ID" =~ ^#.*$ ]] && continue
        [[ -z "$CHANNEL_ID" ]] && continue
        
        export_channel "$CHANNEL_ID" "$CHANNEL_NAME"
        
        # Rate limiting - wait 2 seconds between exports
        sleep 2
    done < "/app/config/channels.txt"
    
    echo "📊 Export completed. Files saved to: $EXPORT_DIR"
    
    # Create manifest file
    cat > "$EXPORT_DIR/manifest.json" << EOF
{
    "export_timestamp": "$TIMESTAMP",
    "export_date": "$(date -Iseconds)",
    "export_format": "json",
    "channels": [
$(find "$EXPORT_DIR" -name "*.json" -not -name "manifest.json" -printf '        "%f",\n' | sed '$ s/,$//')
    ]
}
EOF

else
    echo "❌ Channel configuration file not found: /app/config/channels.txt"
    echo "Create the file with format: CHANNEL_ID,CHANNEL_NAME"
    exit 1
fi