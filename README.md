# Discord Knowledge Graph Pipeline

A system that transforms Discord server conversations into a structured knowledge graph to power LLM-based analysis and insights.

## 🎯 Overview

This project ingests messages from Discord servers, processes and classifies them using LLM-based techniques, extracts semantic relationships as structured triples, and stores them in a knowledge graph for downstream querying and AI integration.

## 🏗️ Architecture

The system follows a 4-layer pipeline architecture:

### 2. Preprocessing Layer

- **Purpose**: Clean, enrich, segment, and classify messages to prepare for extraction and graph construction.

- **Detailed Steps**:

  1. **Preservation**:

     - Retain original message content, including markdown, emojis, mentions, attachments, and system metadata.
     - Preserve all fields from raw Discord JSON including `thread`, `roles`, and `channel`.

  2. **Normalization**:

     - Convert text to lowercase.
     - Normalize whitespace (trim excessive line breaks or spacing).
     - Convert timestamps to ISO 8601 format with timezone (UTC).
     - Flatten nested structures such as `mentions` or `roles` (e.g., store as arrays of names or IDs).

  3. **Segmentation**:

     - Group messages based on Discord thread IDs if available.
     - If not, infer segments using heuristics:
       - Same channel
       - Same author or reply thread
       - Less than 5 minutes apart
     - Each group is tagged with a synthetic `segment_id`

  4. **Classification**:

     - Use LLM-based zero-shot or few-shot classification to tag each message with:
       - `question`, `answer`, `alert`, or `strategy`
     - Store classification metadata with confidence score

- **Storage Strategy**:

  - **Primary**: Store structured `.jsonl` in cloud storage at: `b2://mybucket/preprocessed/YYYYMMDD_HHMM/preprocessed.jsonl`
  - **Optional**: Insert rows into a relational DB table `preprocessed_messages`
    - Indexed by: `segment_id`, `message_id`, `timestamp`, `author`, `type`
    - Use for audit, sampling, UI search, or graph debugging

- **Example Output**:

```json
{
  "message_id": "1322296749183860786",
  "segment_id": "thread-Mega-backdoor-Roth-01",
  "thread": "Mega back door Roth",
  "channel": "#tax-discussion",
  "author": "daveydaveydavedave",
  "timestamp": "2024-12-27T12:15:12-08:00",
  "type": "answer",
  "confidence": 0.88,
  "content": "Right. So if they’ll do the automatic conversion then it’s nothing to worry about...",
  "clean_text": "right. so if they’ll do the automatic conversion then it’s nothing to worry about..."
}
```

### 3. Entity & Relation Extraction Layer

- **Purpose**: Convert messages into structured knowledge triples
- **Granularity**: Per-message extraction
- **Output Format**: JSON triples like `[["user123", "recommends", "BTC breakout"], ["BTC", "has_sentiment", "bullish"]]`

### 4. Query & LLM Integration Layer

- **Purpose**: Use the knowledge graph as structured context for answering natural language questions or generating insights
- **Functionality**:
  - Query the graph for relevant entities, relationships, or subgraphs
  - Use the results to ground LLM-generated answers
  - Construct prompts like:
    ```
    Based on the knowledge graph:
    - Arthur recommends a BTC breakout
    - BTC has bullish sentiment
    → What is Arthur’s outlook on BTC?
    ```
- **Tools**:
  - LangChain's `Neo4jGraph` or `GraphQAChain`
  - Optional: custom Streamlit or CLI-based query interface
- **Input**: Natural language question
- **Output**: LLM-generated, graph-grounded answer
- **Advanced Features**:
  - Subgraph summarization
  - Sentiment/time-based filters
  - Alerts or notifications on graph change events

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
