#!/usr/bin/env bash
set -euo pipefail

: "${DISCORD_TOKEN:?missing}"
: "${GUILD_ID:?missing}"
: "${ARCHIVE_URI:?missing}"
: "${SCOPE:=guild}"
: "${CHANNEL_ID:=}"
: "${AFTER_TS:=1970-01-01}"
: "${EXPORT_FORMAT:=Json}"

mkdir -p /work/exports /work/state
echo "$RCLONE_CONFIG" > /root/.config/rclone/rclone.conf

if [ "$SCOPE" = "guild" ]; then
  /app/DiscordChatExporter.Cli exportguild \
    --token "$DISCORD_TOKEN" \
    --guild "$GUILD_ID" \
    --format "$EXPORT_FORMAT" \
    --after "$AFTER_TS" \
    --output /work/exports \
    --utc
else
  : "${CHANNEL_ID:?missing}"
  /app/DiscordChatExporter.Cli export \
    --token "$DISCORD_TOKEN" \
    --channel "$CHANNEL_ID" \
    --format "$EXPORT_FORMAT" \
    --after "$AFTER_TS" \
    --output /work/exports \
    --utc
fi

date -u +"%Y-%m-%dT%H:%M:%SZ" > /work/exports/_run_completed_at.txt

rclone sync /work/exports "$ARCHIVE_URI" --fast-list --checkers=8 --transfers=8
