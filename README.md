# Discord Knowledge Graph Pipeline

A system that transforms Discord server conversations into a structured knowledge graph to power LLM-based analysis and insights.

## 🎯 Overview

This project ingests messages from Discord servers, processes and classifies them using LLM-based techniques, extracts semantic relationships as structured triples, and stores them in a knowledge graph for downstream querying and AI integration.

## 🏗️ Architecture

The system follows a 3-layer pipeline architecture:

### 1. Ingestion Layer
- **Purpose**: Periodically fetch historical messages from Discord servers
- **Technology**: DiscordChatExporter.Cli via Docker + GitHub Actions
- **Schedule**: Daily automated exports via cron
- **Output**: JSON message dumps stored in cloud storage (B2)

### 2. Preprocessing Layer
- **Purpose**: Clean, enrich, and classify messages for analysis
- **Classification**: Messages categorized as `question`, `answer`, `alert`, `strategy`
- **Method**: LLM-based classification with few-shot prompting
- **Output**: Preprocessed message objects with metadata

### 3. Entity & Relation Extraction Layer
- **Purpose**: Convert messages into structured knowledge triples
- **Granularity**: Per-message extraction
- **Output Format**: JSON triples like `[["user123", "recommends", "BTC breakout"], ["BTC", "has_sentiment", "bullish"]]`

## 🚀 Current Implementation Status

### ✅ Completed
- [x] Docker-based Discord message export system
- [x] GitHub Actions automation for scheduled exports
- [x] Cloud storage integration (Backblaze B2)
- [x] Timestamped folder organization
- [x] Support for both guild-wide and channel-specific exports

### 🚧 In Progress
- [ ] Message preprocessing and classification pipeline
- [ ] LLM-based entity and relation extraction
- [ ] Knowledge graph database setup
- [ ] Query interface development

## 🛠️ Quick Start

### Prerequisites
- Discord bot token with message history access
- Backblaze B2 storage account
- GitHub repository with Actions enabled

### Setup
1. **Configure GitHub Secrets**:
   - `DISCORD_TOKEN`: Your Discord bot token
   - `GUILD_ID`: Discord server ID to export
   - `CHANNEL_ID`: Specific channel ID (if using channel mode)
   - `SCOPE`: Either "guild" or "channel"
   - `RCLONE_CONFIG`: B2 configuration for rclone
   - `ARCHIVE_URI`: B2 bucket path (e.g., `b2:mybucket/discord-archive`)

2. **Run Export**:
   - Automatic: Daily at 09:00 UTC via GitHub Actions
   - Manual: Trigger workflow dispatch in GitHub Actions

3. **Access Data**:
   - Exported JSON files stored in B2 with timestamp folders
   - Format: `YYYYMMDD_HHMMSS/` (e.g., `20250816_140000/`)

## 📁 Project Structure

```
├── .github/workflows/
│   └── export.yml          # GitHub Actions workflow
├── src/discord_kg/
│   ├── ingestion/           # Message ingestion logic
│   ├── preprocessing/       # Message cleaning and classification
│   └── extraction/          # Entity and relation extraction
├── Dockerfile              # Discord exporter container
├── entrypoint.sh           # Export script with logging
├── PRD.md                  # Detailed project requirements
└── ARCHITECTURE_ANALYSIS.md # Technical architecture details
```

## 🔧 Configuration

The system supports flexible export modes:
- **Guild Mode**: Export all channels in a Discord server
- **Channel Mode**: Export specific channel only

Data is automatically organized by timestamp and synced to cloud storage for persistence and analysis.

## 📚 Documentation

- [📘 Project Requirements Document (PRD)](./PRD.md) - Detailed requirements and specifications
- [🏛️ Architecture Analysis](./ARCHITECTURE_ANALYSIS.md) - Technical implementation details

## 🤝 Contributing

This project is in active development. The current focus is on completing the preprocessing and extraction layers.
