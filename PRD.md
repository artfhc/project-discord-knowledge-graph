# 📘 Project Requirements Document (PRD)

## 📌 Title
**Discord Knowledge Graph Pipeline**

## 🧭 Reference
- Original inspiration from this blog: [Augmenting Gemini-1.0-Pro with Knowledge Graphs via LangChain](https://medium.com/google-cloud/augmenting-gemini-1-0-pro-with-knowledge-graphs-via-langchain-bacc2804c423)

## 🎯 Objective
Build a system that ingests messages from a Discord server, processes and classifies them, extracts semantic relationships as structured triples, stores them in a knowledge graph, and enables downstream querying and LLM integration.

---

## 🧱 Architecture Overview

### 1. **Ingestion Layer**
**Goal:** Periodically fetch all historical messages (including threads) across all text channels in a Discord server.

![Ingestion Layer Diagram](https://i.imgur.com/bz0Jm5M.png)

- **Tech:** `discord.py`, cron job
- **Trigger:** Scheduled via cron (e.g., daily)
- **Scope:** All public text channels and associated threads
- **Output:** Raw message dump in JSON format
- **Decisions:**
  - Historical fetch only
  - Threads treated as first-class message blocks
  - No filtering (all message types retained)

### 2. **Preprocessing Layer**
**Goal:** Clean, enrich, and classify each message to prepare for entity/relation extraction.

![Preprocessing Layer Diagram](https://i.imgur.com/ZR8AwU0.png)

- **Cleaning:**
  - Preserve markdown, emojis, code snippets, and mentions
  - Normalize case and spacing only

- **Classification:**
  - Message types: `question`, `answer`, `alert`, `strategy`
  - Done via LLM-based classification with few-shot prompt

- **Segmentation:**
  - Grouped by thread
  - Standalone messages in channels assigned synthetic threads

- **Output:** List of preprocessed message objects with metadata

### 3. **Entity & Relation Extraction Layer**
**Goal:** Convert each message into one or more structured triples for graph construction.

![Triple Extraction Diagram](https://i.imgur.com/3Ei9NhH.png)

- **Granularity:** Per message (not per thread)
- **Method:** LLM extraction with controlled output format
- **Output Format:**
  ```json
  [
    ["user123", "recommends", "BTC breakout"],
    ["BTC", "has_sentiment", "bullish"]
  ]
