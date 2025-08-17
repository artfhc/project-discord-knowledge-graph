# Discord Message Preprocessing

Local implementation of the preprocessing layer using BART-MNLI for message classification.

## Features

- **Message Preservation**: Retains original Discord metadata (roles, mentions, attachments, reactions)
- **Text Normalization**: Cleans and normalizes message content while preserving meaning
- **Message Segmentation**: Groups related messages using thread IDs and temporal heuristics
- **Zero-shot Classification**: Uses BART-MNLI to classify messages into: `question`, `answer`, `alert`, `strategy`
- **Local Processing**: Runs entirely locally without API dependencies

## Quick Start

### 1. Install Dependencies

```bash
cd src/discord_kg/preprocessing
pip install -r requirements.txt
```

### 2. Run Preprocessing Pipeline

```bash
# Full pipeline (preprocessing + classification)
python test_local.py general.json --output results.jsonl

# Preprocessing only
python test_local.py general.json --preprocess-only --output preprocessed.jsonl

# Classification only (on preprocessed data)
python test_local.py preprocessed.jsonl --classify-only --output classified.jsonl
```

### 3. View Results

The output is a JSONL file where each line contains a classified message:

```json
{
  "message_id": "1322296749183860786",
  "segment_id": "thread-mega-back-door-roth",
  "thread": "Mega back door Roth",
  "channel": "general",
  "author": "daveydaveydavedave",
  "timestamp": "2024-12-27T20:15:12+00:00",
  "type": "answer",
  "confidence": 0.88,
  "content": "Right. So if they'll do the automatic conversion...",
  "clean_text": "right. so if they'll do the automatic conversion...",
  "original_timestamp": "2024-12-27T12:15:12-08:00",
  "author_id": "142029206535143424",
  "author_roles": ["Owners", "Head mod"],
  "mentions": [],
  "attachments": [],
  "reactions": [],
  "is_bot": false,
  "is_pinned": false,
  "reply_to": null
}
```

## Architecture

### Files

- `preprocessor.py`: Message preprocessing pipeline (preservation, normalization, segmentation)
- `classifier.py`: BART-MNLI-based message classification
- `test_local.py`: Testing script for the complete pipeline
- `create_sample.py`: Utility to create smaller samples from large Discord exports
- `requirements.txt`: Python dependencies
- `general.json`: Sample Discord export data
- `sample.json`, `sample_1k.json`: Sample data files for testing

### Pipeline Steps

1. **Preservation**: Extract and preserve Discord metadata
2. **Normalization**: Clean text and normalize timestamps to ISO 8601 UTC
3. **Segmentation**: Group messages by thread ID or channel+author+time heuristics  
4. **Classification**: Use zero-shot BART-MNLI to classify message types with confidence scores

### Message Types

- `question`: Questions or requests for information
- `answer`: Responses or informational content
- `alert`: Notifications, warnings, or urgent messages
- `strategy`: Strategic discussions or recommendations

## Configuration

### Model Selection

Change the classification model by passing `--model` parameter:

```bash
python test_local.py general.json --model "microsoft/DialoGPT-medium"
```

### Sample Data Creation

Create smaller samples from large Discord exports for testing:

```bash
# Create a random sample of 1000 messages
python create_sample.py general.json --output sample_1k.json --sample-size 1000 --random

# Create a sequential sample of 500 messages
python create_sample.py general.json --output sample_500.json --sample-size 500
```

### Custom Segmentation

Modify `generate_segment_id()` in `preprocessor.py` to adjust message grouping logic.

### Output Format

The preprocessor outputs structured JSONL compatible with the project architecture described in the main README.

## Performance

- **BART-MNLI**: ~10-20 messages/second on CPU, ~100+ messages/second on GPU
- **Memory**: ~1-2GB RAM for model loading
- **Storage**: Processed messages are ~2-3x larger than raw Discord export due to metadata preservation

## Next Steps

- Integrate with cloud storage (B2) for batch processing
- Add support for Modal/serverless deployment
- Implement incremental processing for large datasets
- Add evaluation metrics for classification accuracy