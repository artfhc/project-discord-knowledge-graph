# Discord Knowledge Graph Pipeline

A system that transforms Discord server conversations into a structured knowledge graph to power LLM-based analysis and insights.

## 🎯 Overview

This project ingests messages from Discord servers, processes and classifies them using LLM-based techniques, extracts semantic relationships as structured triples, and stores them in a knowledge graph for downstream querying and AI integration.

## 🏗️ Architecture

The system follows a 4-layer pipeline architecture:

### 1. Ingestion Layer

- **Purpose**: Periodically fetch historical messages from Discord servers
- **Technology**: DiscordChatExporter.Cli via Docker + GitHub Actions
- **Schedule**: Daily automated exports via cron
- **Output**: JSON message dumps stored in cloud storage (B2)

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

- **Comparison of Classification Options**:

| Option             | Model           | Infra           | Speed    | Cost Estimate (1M msgs) | Batch Support | Notes                               |
| ------------------ | --------------- | --------------- | -------- | ----------------------- | ------------- | ----------------------------------- |
| OpenAI GPT-3.5     | Zero/few-shot   | API (OpenAI)    | Slow–Med | \~\$400–500 unbatched   | ✅ Yes         | Great accuracy, expensive unbatched |
| Claude 3 Haiku     | Zero/few-shot   | API (Anthropic) | Med      | \~\$100–200 batched     | ✅ Yes         | Good value, 200K token context      |
| Cohere Classify    | Custom model    | API (Cohere)    | Fast     | \~\$80–150 batched      | ✅ Yes         | Native classification endpoint      |
| TinyBERT           | Distilled BERT  | Self-hosted     | Fast     | \~\$10–20 GPU infra     | ✅ Yes         | Best for cheap, large-scale runs    |
| DistilBERT         | Distilled BERT  | Self-hosted     | Fast     | \~\$10–30 GPU infra     | ✅ Yes         | Slightly larger, still efficient    |
| vLLM w/ GPTQ model | Open LLM (GGUF) | Self-hosted     | Fast     | \~\$20–50 infra         | ✅ Yes         | Depends on GPU and batching config  |

  ### 3. Entity & Relation Extraction Layer

- **Purpose**: Convert preprocessed messages into structured knowledge triples.

- **Input**: Preprocessed `.jsonl` messages with `segment_id`, `type`, `author`, and `clean_text` from Step 2.

- **Process**:

  - For each message, use LLM or rule-based extraction to emit structured triples (subject, predicate, object).
  - The extraction strategy depends on the message `type` from Step 2:
    - `strategy`: extract subjects and verbs related to investment techniques (e.g., ["user123", "discusses", "covered call strategy"])
    - `alert`: extract notification content and audience (e.g., ["user456", "alerts", "all\_members about CPI release"])
    - `question`: extract question topics (e.g., ["user789", "asks\_about", "Mega Backdoor Roth"])
    - `answer`: extract response linkage or factual statements
    - `signal`: extract asset, action, and timing (e.g., ["user321", "recommends", "Buy BTC at \$60K"])
    - `analysis`: extract target asset and key insights (e.g., ["user777", "analyzes", "Tesla Q4 earnings"])
    - `performance`: extract P&L claims or strategy metrics (e.g., ["user999", "reports\_return", "+12% on breakout strategy"])
    - `discussion`: extract debate topics or opinions optionally

- **Linking Q&A**:

  - Within each segment, if a `question` is found, scan for the nearest `answer` that:
    - Appears shortly after the question
    - Mentions or replies to the same user
    - Is within 5–10 messages or 10 minute window
  - Emit a link:
    ```json
    ["question_msg_123", "answered_by", "answer_msg_456"]
    ```
  - Optionally, match semantically using embeddings or cosine similarity

- **Output Format**:

  - Triples like:
    ```json
    ["user123", "recommends", "BTC breakout"]
    ["msg456", "answered_by", "msg789"]
    ```
  - With metadata: `message_id`, `timestamp`, `confidence_score`, `segment_id`

- **Enhancements**:

  - Normalize entities across variants (e.g., "btc" = "Bitcoin")
  - Attach user role metadata for trust evaluation
  - Use `type` to select different prompt templates or extraction strategies

- **Model Comparison Table for Step 3**:

| **Option**                        | **Approach**         | **Infra**       | **Speed** | **Cost (per 1M msgs)** | **Pros**                                                      | **Cons**                                       | **Use When**                                         |
| --------------------------------- | -------------------- | --------------- | --------- | ---------------------- | ------------------------------------------------------------- | ---------------------------------------------- | ---------------------------------------------------- |
| **OpenAI GPT-4 / GPT-3.5**        | Prompted LLM (RAG)   | API (OpenAI)    | Slow–Med  | \~\$500–\$800          | High accuracy, can extract complex triples with minimal setup | High cost, slow inference                      | You need max accuracy or one-off high-quality runs   |
| **Claude 3 Haiku**                | Prompted LLM (RAG)   | API (Anthropic) | Medium    | \~\$200–\$400          | Fast, accurate, large context window (200k tokens)            | Still costly for real-time or high volume      | Balanced cost/accuracy; ideal for segment-level jobs |
| **DistilBERT + Rule-Based**       | NER + Template Match | Self-hosted     | Fast      | \~\$10–\$30 (GPU)      | Cheap, good for predictable patterns (e.g. signals, alerts)   | Requires hand-tuned rules/templates            | You have clear rules for each message type           |
| **SpaCy + Custom Rules**          | Rule-Based NLP       | Local / Server  | Very fast | \~\$5–\$10 infra       | Fast, fully local, great for extracting names, tickers, dates | Not good with fuzzy logic or creative phrasing | Preprocessing & light-weight pipelines               |
| **HuggingFace BART (fine-tuned)** | Sequence-to-Triple   | Self-hosted GPU | Medium    | \~\$50–\$100           | Can extract triples directly; flexible                        | Requires fine-tuning + GPU infra               | You want structured triples and control              |
| **LLM + Sentence Transformers**   | Embedding Clustering | Local / Hybrid  | Medium    | \~\$30–\$100           | Semantic similarity for Q&A, links, cluster analysis          | Not pure triple extraction                     | Linking Q&A / dedup / summary tasks                  |

- **Message-Type Strategy Map**:

| **Message Type** | **Best Model / Strategy**                                 |
| ---------------- | --------------------------------------------------------- |
| `signal`         | Rule-based pattern + NER (e.g., “Buy BTC at \$60K”)       |
| `alert`          | Regex / SpaCy pipeline (e.g., “Reminder: FOMC today!”)    |
| `strategy`       | Claude or DistilBERT + rule hybrid                        |
| `analysis`       | Claude / GPT (more abstract reasoning needed)             |
| `question`       | Light NLP + Q/A linker using timestamp + semantic search  |
| `answer`         | Embed-based semantic match + linking to previous question |
| `performance`    | Regex or BERT for P&L, % returns, benchmark terms         |
| `discussion`     | Usually skipped or lightly summarized                     |

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
- **Advanced Features**:
  - Subgraph summarization
  - Sentiment/time-based filters
  - Alerts or notifications on graph change events

---

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
