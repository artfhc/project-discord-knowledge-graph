# 📘 Step 3: Entity & Relation Extraction Layer

This stage transforms classified and segmented Discord messages into structured triples suitable for knowledge graph construction.

---

## 🎯 Purpose

Convert preprocessed messages into machine-readable relationships (subject–predicate–object) using a combination of classification cues and LLM/NLP techniques.

---

## 🧩 Inputs

- Preprocessed `.jsonl` files from Step 2
- Each message includes:
  - `segment_id`
  - `message_id`
  - `type` (from classification step)
  - `author`
  - `timestamp`
  - `clean_text`
  - `confidence`

---

## ⚙️ Processing Logic

### 📚 Message Type → Extraction Strategy

| **Message Type** | **Extraction Method**                                      | **Examples of Triples**                                                                 |
|------------------|-------------------------------------------------------------|------------------------------------------------------------------------------------------|
| `question`       | LLM w/ `asks_about`, optionally linked to answers           | `["user123", "asks_about", "Mega Backdoor Roth"]`                                       |
| `answer`         | LLM + Q/A linker logic                                       | `["msg456", "answered_by", "msg789"]`                                                   |
| `alert`          | Rule-based / Regex                                          | `["user456", "alerts", "all_members about CPI release"]`                                |
| `strategy`       | LLM + rule-based triple extraction                          | `["user123", "recommends", "covered call strategy"]`                                    |
| `signal`         | NER + pattern match                                         | `["user321", "recommends", "Buy BTC at $60K"]`                                          |
| `performance`    | Regex / Pattern match for %, benchmarks                     | `["user111", "reports_return", "+15% on momentum strategy"]`                            |
| `analysis`       | LLM extraction, supports abstract reasoning                 | `["user444", "analyzes", "Tesla Q4 earnings outlook"]`                                  |
| `discussion`     | Optionally summarized, or light pattern matching            | `["user222", "shares_opinion", "on market trends"]`                                     |

---

## 🔗 Q&A Linking Logic

- If a `question` is found in a segment, find the most likely `answer` using:
  - Reply reference
  - Mentions
  - Timestamp proximity (≤ 10 mins or 10 messages)
  - Cosine similarity on embeddings (optional)

### Example:
```json
["msg123", "answered_by", "msg456"]
```

---

## 📤 Output Format

Each triple is stored as:

```json
{
  "subject": "user123",
  "predicate": "recommends",
  "object": "Buy BTC at $60K",
  "message_id": "1322296749183860786",
  "segment_id": "thread-Mega-backdoor-Roth-01",
  "timestamp": "2024-12-27T12:15:12-08:00",
  "confidence": 0.87
}
```

---

## 📦 Storage

- Cloud JSONL files: `b2://mybucket/triples/YYYYMMDD_HHMM/triples.jsonl`
- Optional Neo4j insert: Create nodes and edges using `subject`, `predicate`, `object` fields.

---

## 🧠 Model Options and Tradeoffs

| **Option**                | **Approach**             | **Infra**        | **Speed** | **Cost (1M msgs)** | **Pros**                                                  | **Cons**                                    |
|---------------------------|--------------------------|------------------|-----------|--------------------|-----------------------------------------------------------|---------------------------------------------|
| OpenAI GPT-3.5            | LLM w/ prompt            | OpenAI API       | Med       | ~$400–500          | High quality, zero setup                                  | Costly, slower                             |
| Claude 3 Haiku            | LLM w/ prompt            | Anthropic API    | Fast      | ~$150–300          | Fast, large context, accurate                             | Still costly for high volume               |
| DistilBERT + Rules        | NER + pattern match      | Self-hosted GPU  | Fast      | ~$10–30            | Cheap, scalable                                           | Needs custom rule sets                     |
| SpaCy + Custom Rules      | NLP + templates          | Local            | Very Fast | ~$5–10             | Best for alerts and signals                               | Can't handle abstract content              |
| BART Fine-tuned           | Seq2Triple               | Self-hosted GPU  | Medium    | ~$50–100           | Custom triple extraction                                 | Needs training                             |

---

## 🏷️ Batching Considerations

| **Batch Size** | **Cost Efficiency** | **Inference Speed** | **Quality Risk**             |
|----------------|---------------------|----------------------|-------------------------------|
| 10–20 msgs     | 🔴 Low               | 🔴 Slow               | 🔵 Most accurate               |
| 50–100 msgs    | 🟡 Balanced          | 🟡 Acceptable         | 🟡 Minor drop in context depth |
| 200+ msgs      | 🟢 Cheap             | 🟢 Fast               | 🔴 Loss in message context     |

---

## ✅ Best Practices

- Use `segment_id` as the unit of context window for LLM prompts
- Cache extracted triples for deduplication and correction
- Normalize all entity variants before graph ingestion
- Consider semantic grouping of triples per topic/thread