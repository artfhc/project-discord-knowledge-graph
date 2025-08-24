# Thread ID Management Guide

This guide explains how to find, manage, and use thread IDs for checkpoint replay functionality.

## 🆔 What is a Thread ID?

A **thread ID** is a unique identifier that LangGraph uses to:
- Save checkpoint states during processing
- Resume workflows from specific points
- Enable replay of individual nodes or extraction types

Think of it like a "save game" name in a video game!

## 🔍 How to Find Your Thread ID

### Method 1: You Choose the Thread ID (Recommended)

When you start a workflow, **YOU** specify the thread ID:

```bash
# You create the thread ID name
python extractor_langgraph.py messages.jsonl output.jsonl \
  --provider claude \
  --enable-checkpoints \
  --thread-id my-extraction-session-001
```

**💡 Best Practices for Thread ID Names:**
- Use descriptive names: `discord_trading_msgs_20240824`
- Include date/time: `extraction_session_20240824_1430`
- Include file info: `messages_1k_claude_test`
- Keep them short but meaningful

### Method 2: Auto-Generate Thread ID

Let the system create a unique thread ID for you:

```bash
# System generates: messages_a1b2c3d4_20240824_143052
python extractor_langgraph.py messages.jsonl output.jsonl \
  --provider claude \
  --auto-thread-id
```

**Auto-generated format:** `{filename}_{hash}_{timestamp}`

### Method 3: List Available Checkpoints

```bash
# See what checkpoints are available (future feature)
python extractor_langgraph.py --list-checkpoints
```

## 📋 Thread ID Workflow Examples

### Example 1: Long Processing Job

```bash
# Step 1: Start with checkpoints enabled
python extractor_langgraph.py big_dataset.jsonl output.jsonl \
  --provider claude \
  --enable-checkpoints \
  --thread-id big-job-20240824

# Step 2: If it fails or stops, resume with same thread ID
python extractor_langgraph.py big_dataset.jsonl output.jsonl \
  --provider claude \
  --thread-id big-job-20240824  # Same ID = auto-resume!
```

### Example 2: Debugging Q&A Linking

```bash
# Step 1: Initial run (assume Q&A linking fails)
python extractor_langgraph.py messages.jsonl output.jsonl \
  --provider claude \
  --enable-checkpoints \
  --thread-id debug-qa-session

# Step 2: Replay just Q&A linking with different settings
python extractor_langgraph.py messages.jsonl output.jsonl \
  --provider claude \
  --thread-id debug-qa-session \
  --replay-from-node qa_linking
```

### Example 3: Testing Single Message Types

```bash
# Step 1: Process everything
python extractor_langgraph.py messages.jsonl output.jsonl \
  --provider claude \
  --enable-checkpoints \
  --thread-id test-types-001

# Step 2: Debug just question extraction
python extractor_langgraph.py messages.jsonl output.jsonl \
  --provider claude \
  --thread-id test-types-001 \
  --replay-specific-extraction question

# Step 3: Debug just strategy extraction  
python extractor_langgraph.py messages.jsonl output.jsonl \
  --provider claude \
  --thread-id test-types-001 \
  --replay-specific-extraction strategy
```

## 🗂️ Keeping Track of Thread IDs

### Simple Log File Approach

Create a `thread_ids.log` file:

```bash
# Keep a log of your thread IDs
echo "$(date): big-job-20240824 - Processing 10k Discord messages with Claude" >> thread_ids.log
echo "$(date): debug-qa-session - Testing Q&A linking improvements" >> thread_ids.log
echo "$(date): test-types-001 - Debugging extraction types individually" >> thread_ids.log
```

### Descriptive Naming Convention

Use a consistent naming pattern:

```bash
# Pattern: {project}_{dataset}_{provider}_{date}_{purpose}
--thread-id discord_trading_claude_20240824_production
--thread-id discord_qa_openai_20240824_debugging  
--thread-id messages_1k_claude_20240824_testing
```

## 🔄 Common Replay Scenarios

### Scenario 1: "Process Failed Halfway"

**Problem:** Processing stopped due to API rate limits or network issues.

**Solution:**
```bash
# Resume from where it left off
python extractor_langgraph.py messages.jsonl output.jsonl \
  --provider claude \
  --thread-id your-original-thread-id
```

### Scenario 2: "Q&A Linking Produced Bad Results"

**Problem:** Q&A linking didn't work well, want to try different approach.

**Solution:**
```bash
# Replay just Q&A linking
python extractor_langgraph.py messages.jsonl output.jsonl \
  --provider claude \
  --thread-id your-original-thread-id \
  --replay-from-node qa_linking
```

### Scenario 3: "Question Extraction Looks Wrong"

**Problem:** Question extraction results need debugging.

**Solution:**
```bash
# Test just question extraction
python extractor_langgraph.py messages.jsonl output.jsonl \
  --provider claude \
  --thread-id your-original-thread-id \
  --replay-specific-extraction question
```

## ⚠️ Important Notes

### Current Limitation: In-Memory Storage

**The current system uses `MemorySaver`**, which means:
- ✅ Checkpoints work during a single session
- ❌ Checkpoints are lost when you restart the Python process
- ❌ Can't resume from yesterday's checkpoints

### Future Enhancement: Persistent Storage

To make checkpoints permanent, the system would need:
- `SQLiteCheckpointSaver` instead of `MemorySaver`
- Checkpoint files stored in `./checkpoints/` directory
- Proper checkpoint cleanup and management

## 🎯 Quick Reference

| What You Want | Command |
|---------------|---------|
| Start with checkpoints | `--enable-checkpoints --thread-id my-session` |
| Resume failed job | `--thread-id my-session` (same ID) |
| Replay from Q&A linking | `--thread-id my-session --replay-from-node qa_linking` |
| Debug single type | `--thread-id my-session --replay-specific-extraction question` |
| Auto-generate ID | `--auto-thread-id` |
| List checkpoints | `--list-checkpoints` |

## 💡 Pro Tips

1. **Always use descriptive thread IDs** - you'll thank yourself later!
2. **Keep a log** of what each thread ID was used for
3. **Use date/time** in thread IDs for easy organization
4. **Test replay** on small datasets before using on large ones
5. **Remember**: Current checkpoints are in-memory only

The thread ID system gives you powerful debugging and recovery capabilities - use descriptive names and you'll never lose track of your processing sessions! 🚀