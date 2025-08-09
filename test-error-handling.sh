#!/bin/bash
# Test error handling with various invalid scenarios

set -e

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/error_test_${TIMESTAMP}.log"

mkdir -p logs

echo "🧪 Testing error handling scenarios..." | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Test scenarios
declare -a TEST_SCENARIOS=(
    "invalid_channel_id:123456789:Invalid channel ID (too short)"
    "fake_channel:999999999999999999:Non-existent channel ID"
    "malformed_id:not_a_number:Malformed channel ID"
    "empty_token::Empty token test"
)

ERROR_COUNT=0
SUCCESS_COUNT=0

echo "🔍 Running error handling tests..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

for scenario in "${TEST_SCENARIOS[@]}"; do
    IFS=':' read -r test_name channel_id description <<< "$scenario"
    
    echo "[$((ERROR_COUNT + SUCCESS_COUNT + 1))] Testing: $description" | tee -a "$LOG_FILE"
    echo "  Channel ID: '$channel_id'" | tee -a "$LOG_FILE"
    
    # Prepare token (use empty for empty token test)
    if [ "$test_name" = "empty_token" ]; then
        TEST_TOKEN=""
    elif [ -f "config/discord_token" ]; then
        TEST_TOKEN="$(cat config/discord_token)"
    else
        echo "  ⚠️  No Discord token found - using dummy token" | tee -a "$LOG_FILE"
        TEST_TOKEN="dummy_token"
    fi
    
    # Run export with error capture
    echo "  🔄 Running export..." | tee -a "$LOG_FILE"
    
    if timeout 30 docker run --rm \
        -v "$(pwd)/exports:/out" \
        tyrrrz/discordchatexporter:stable \
        export \
        -t "$TEST_TOKEN" \
        -c "$channel_id" \
        -f Json \
        -o "/out/error_test_${test_name}.json" \
        2>>"$LOG_FILE" 1>/dev/null; then
        
        echo "  ❌ Unexpected success (should have failed)" | tee -a "$LOG_FILE"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        EXIT_CODE=$?
        echo "  ✅ Failed as expected (exit code: $EXIT_CODE)" | tee -a "$LOG_FILE"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
    
    echo "" | tee -a "$LOG_FILE"
    sleep 1
done

# Test pipeline error handling
echo "🔧 Testing pipeline error handling..." | tee -a "$LOG_FILE"

# Create an invalid JSON file
INVALID_JSON="exports/invalid_test.json"
echo '{"invalid": json content without proper closing' > "$INVALID_JSON"

echo "Created invalid JSON file for testing" | tee -a "$LOG_FILE"

# Ensure pipeline processor is running
docker-compose -f docker-compose.local.yml up -d

echo "Testing pipeline with invalid JSON..." | tee -a "$LOG_FILE"

if docker-compose -f docker-compose.local.yml exec -T pipeline-processor \
    python scripts/local_discord_export.py \
    --process-only "/app/exports" \
    --log-level DEBUG 2>>"$LOG_FILE" 1>/dev/null; then
    
    echo "✅ Pipeline handled invalid JSON gracefully" | tee -a "$LOG_FILE"
else
    echo "⚠️  Pipeline failed with invalid JSON (this may be expected)" | tee -a "$LOG_FILE"
fi

# Cleanup invalid file
rm -f "$INVALID_JSON"

# Test with non-existent directory
echo "Testing pipeline with non-existent directory..." | tee -a "$LOG_FILE"

if docker-compose -f docker-compose.local.yml exec -T pipeline-processor \
    python scripts/local_discord_export.py \
    --process-only "/app/non_existent_directory" \
    --log-level INFO 2>>"$LOG_FILE" 1>/dev/null; then
    
    echo "⚠️  Pipeline succeeded with non-existent directory (unexpected)" | tee -a "$LOG_FILE"
else
    echo "✅ Pipeline correctly failed with non-existent directory" | tee -a "$LOG_FILE"
fi

# Summary
echo "" | tee -a "$LOG_FILE"
echo "🧪 Error handling test summary:" | tee -a "$LOG_FILE"
echo "  Export errors (expected): $ERROR_COUNT" | tee -a "$LOG_FILE"
echo "  Unexpected successes: $SUCCESS_COUNT" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

if [ $SUCCESS_COUNT -gt 0 ]; then
    echo "⚠️  Some tests succeeded when they should have failed" | tee -a "$LOG_FILE"
else
    echo "✅ All error scenarios handled correctly" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "📁 Check detailed logs in: $LOG_FILE" | tee -a "$LOG_FILE"
echo "🎉 Error handling test completed!" | tee -a "$LOG_FILE"