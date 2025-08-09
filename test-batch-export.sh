#!/bin/bash
# Batch export multiple Discord channels with error handling and pipeline testing

set -e

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
EXPORT_DIR="exports/batch_${TIMESTAMP}"
LOG_FILE="logs/batch_export_${TIMESTAMP}.log"

# Create directories
mkdir -p exports logs "$EXPORT_DIR"

echo "🚀 Starting batch Discord export test..." | tee -a "$LOG_FILE"
echo "Export directory: $EXPORT_DIR" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Check if channels.txt exists
if [ ! -f "config/channels.txt" ]; then
    echo "❌ Error: config/channels.txt not found!" | tee -a "$LOG_FILE"
    echo "Create the file with channel IDs (one per line): CHANNEL_ID,CHANNEL_NAME" | tee -a "$LOG_FILE"
    exit 1
fi

# Check if Discord token exists
if [ ! -f "config/discord_token" ]; then
    echo "❌ Error: config/discord_token not found!" | tee -a "$LOG_FILE"
    echo "Create the file with your Discord token" | tee -a "$LOG_FILE"
    exit 1
fi

# Ensure pipeline processor is running
echo "🐳 Starting pipeline processor..." | tee -a "$LOG_FILE"
docker-compose -f docker-compose.local.yml up -d

# Counters for statistics
TOTAL_CHANNELS=0
SUCCESSFUL_EXPORTS=0
FAILED_EXPORTS=0
EXPORTED_FILES=()

echo "📥 Processing channels from config/channels.txt..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Process each channel
while IFS=',' read -r CHANNEL_ID CHANNEL_NAME || [ -n "$CHANNEL_ID" ]; do
    # Skip comments and empty lines
    [[ "$CHANNEL_ID" =~ ^#.*$ ]] && continue
    [[ -z "$CHANNEL_ID" ]] && continue
    
    # Trim whitespace
    CHANNEL_ID=$(echo "$CHANNEL_ID" | xargs)
    CHANNEL_NAME=$(echo "$CHANNEL_NAME" | xargs)
    
    # Use channel ID as name if name is empty
    [ -z "$CHANNEL_NAME" ] && CHANNEL_NAME="channel_${CHANNEL_ID}"
    
    TOTAL_CHANNELS=$((TOTAL_CHANNELS + 1))
    OUTPUT_FILE="${EXPORT_DIR}/${CHANNEL_NAME}_${CHANNEL_ID}.json"
    
    echo "[$TOTAL_CHANNELS] 🔄 Exporting: $CHANNEL_NAME ($CHANNEL_ID)" | tee -a "$LOG_FILE"
    
    # Export with error handling
    if docker run --rm \
        -v "$(pwd)/exports:/out" \
        -v "$(pwd)/config:/config:ro" \
        tyrrrz/discordchatexporter:stable \
        export \
        -t "$(cat config/discord_token)" \
        -c "$CHANNEL_ID" \
        -f Json \
        -o "/out/batch_${TIMESTAMP}/${CHANNEL_NAME}_${CHANNEL_ID}.json" \
        2>>"$LOG_FILE"; then
        
        # Check if file was actually created
        if [ -f "$OUTPUT_FILE" ]; then
            FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
            SUCCESSFUL_EXPORTS=$((SUCCESSFUL_EXPORTS + 1))
            EXPORTED_FILES+=("$OUTPUT_FILE")
            
            echo "    ✅ Success! Size: $FILE_SIZE" | tee -a "$LOG_FILE"
            
            # Try to get message count if jq is available
            if command -v jq &> /dev/null; then
                MESSAGE_COUNT=$(jq '.messages | length' "$OUTPUT_FILE" 2>/dev/null || echo "unknown")
                echo "    📊 Messages: $MESSAGE_COUNT" | tee -a "$LOG_FILE"
            fi
        else
            echo "    ❌ Failed: File not created" | tee -a "$LOG_FILE"
            FAILED_EXPORTS=$((FAILED_EXPORTS + 1))
        fi
    else
        echo "    ❌ Failed: Export command failed" | tee -a "$LOG_FILE"
        FAILED_EXPORTS=$((FAILED_EXPORTS + 1))
    fi
    
    # Rate limiting - wait between exports
    echo "    ⏳ Waiting 2 seconds..." | tee -a "$LOG_FILE"
    sleep 2
    echo "" | tee -a "$LOG_FILE"
    
done < config/channels.txt

# Export Summary
echo "📊 Export Summary:" | tee -a "$LOG_FILE"
echo "  Total channels processed: $TOTAL_CHANNELS" | tee -a "$LOG_FILE"
echo "  Successful exports: $SUCCESSFUL_EXPORTS" | tee -a "$LOG_FILE"
echo "  Failed exports: $FAILED_EXPORTS" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

if [ $SUCCESSFUL_EXPORTS -eq 0 ]; then
    echo "❌ No successful exports - stopping pipeline test" | tee -a "$LOG_FILE"
    exit 1
fi

# Test Pipeline Processing
echo "🔄 Testing pipeline processing on exported files..." | tee -a "$LOG_FILE"

if docker-compose -f docker-compose.local.yml exec -T pipeline-processor \
    python scripts/process_exported_files.py \
    "/app/exports/batch_${TIMESTAMP}" \
    --log-level INFO 2>>"$LOG_FILE"; then
    
    echo "✅ Pipeline processing completed successfully!" | tee -a "$LOG_FILE"
else
    echo "❌ Pipeline processing failed - check logs" | tee -a "$LOG_FILE"
fi

# Final Summary
echo "" | tee -a "$LOG_FILE"
echo "🎉 Batch export test completed!" | tee -a "$LOG_FILE"
echo "Export directory: $EXPORT_DIR" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"

# List all exported files
if [ ${#EXPORTED_FILES[@]} -gt 0 ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "📁 Exported files:" | tee -a "$LOG_FILE"
    for file in "${EXPORTED_FILES[@]}"; do
        echo "  - $(basename "$file")" | tee -a "$LOG_FILE"
    done
fi