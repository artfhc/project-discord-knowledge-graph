#!/usr/bin/env bash
set -euo pipefail

echo "=== Discord Chat Exporter Starting ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

: "${DISCORD_TOKEN:?missing}"
: "${GUILD_ID:?missing}"
: "${ARCHIVE_URI:?missing}"
: "${SCOPE:=guild}"
: "${CHANNEL_ID:=}"
: "${AFTER_TS:=1970-01-01}"
: "${EXPORT_FORMAT:=Json}"

echo "=== Configuration ==="
echo "GUILD_ID: $GUILD_ID"
echo "SCOPE: $SCOPE"
echo "CHANNEL_ID: ${CHANNEL_ID:-"(not set)"}"
echo "AFTER_TS: $AFTER_TS"
echo "EXPORT_FORMAT: $EXPORT_FORMAT"
echo "ARCHIVE_URI: $ARCHIVE_URI"
echo "DISCORD_TOKEN: ${DISCORD_TOKEN:0:10}..." # Only show first 10 chars for security

echo "=== Setting up directories and rclone ==="
mkdir -p /work/exports /work/state /root/.config/rclone

# Check if RCLONE_CONFIG is set
if [ -z "${RCLONE_CONFIG:-}" ]; then
  echo "ERROR: RCLONE_CONFIG environment variable is not set"
  exit 1
fi

# Write rclone config, ensuring proper line endings
printf "%s\n" "$RCLONE_CONFIG" > /root/.config/rclone/rclone.conf
echo "Created rclone config and work directories"
echo "Rclone config file contents:"
cat /root/.config/rclone/rclone.conf
echo "--- End of rclone config ---"

# Test rclone config
echo "Testing rclone config:"
rclone config show

if [ "$SCOPE" = "guild" ]; then
  echo "=== Exporting entire guild ==="
  echo "Running: DiscordChatExporter.Cli exportguild --guild $GUILD_ID --format $EXPORT_FORMAT --after $AFTER_TS"
  /app/DiscordChatExporter.Cli exportguild \
    --token "$DISCORD_TOKEN" \
    --guild "$GUILD_ID" \
    --format "$EXPORT_FORMAT" \
    --after "$AFTER_TS" \
    --output /work/exports \
    --utc
else
  : "${CHANNEL_ID:?missing}"
  echo "=== Exporting specific channel ==="
  echo "Running: DiscordChatExporter.Cli export --channel $CHANNEL_ID --format $EXPORT_FORMAT --after $AFTER_TS"
  /app/DiscordChatExporter.Cli export \
    --token "$DISCORD_TOKEN" \
    --channel "$CHANNEL_ID" \
    --format "$EXPORT_FORMAT" \
    --after "$AFTER_TS" \
    --output /work/exports \
    --utc
fi

echo "=== Export completed ==="
echo "Files in /work/exports:"
ls -la /work/exports/

date -u +"%Y-%m-%dT%H:%M:%SZ" > /work/exports/_run_completed_at.txt

echo "=== Syncing to archive ==="
echo "Running: rclone sync /work/exports $ARCHIVE_URI"
rclone sync /work/exports "$ARCHIVE_URI" --fast-list --checkers=8 --transfers=8

echo "=== Discord Chat Exporter Completed Successfully ==="
echo "Completion timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
