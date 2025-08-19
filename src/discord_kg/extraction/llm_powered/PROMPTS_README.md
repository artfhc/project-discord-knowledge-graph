# 📝 YAML Prompt Configuration

The LLM extractor now uses YAML files for prompt configuration, making it easier to modify and experiment with different prompts without changing the code.

## 📁 Files

- **`prompts.yaml`** - Main prompt configuration file
- **`test_yaml_prompts.py`** - Test script to validate YAML loading

## 🏗️ Structure

The YAML configuration has three main sections:

### 1. System Prompt
```yaml
system:
  content: |
    The main system prompt that defines the LLM's role and rules
```

### 2. Message Type Templates
```yaml
templates:
  question:
    description: "What this template does"
    instruction: |
      Template with {message_text} placeholder
  strategy:
    # ... similar structure
```

### 3. Configuration Settings
```yaml
config:
  confidence_scores:
    question: 0.85
    strategy: 0.88
    # ... scores for each message type
  
  predicates:
    question: ["asks_about"]
    strategy: ["recommends", "discusses_strategy"]
    # ... expected predicates for each type
```

## 🚀 Usage

### Default Configuration
```python
# Uses ./prompts.yaml automatically
from extractor_llm import PromptTemplates
templates = PromptTemplates()
```

### Custom Configuration
```python
# Use custom YAML file
templates = PromptTemplates("/path/to/custom_prompts.yaml")
```

### Command Line
```bash
# Use default prompts.yaml
python extractor_llm.py input.jsonl output.jsonl --provider openai

# Use custom config file
python extractor_llm.py input.jsonl output.jsonl --provider openai --config custom_prompts.yaml
```

## 🧪 Testing

Test your prompt configuration:

```bash
# Test default configuration
python test_yaml_prompts.py

# Test with virtual environment
source ../preprocessing/venv/bin/activate
python test_yaml_prompts.py
```

## ✏️ Editing Prompts

### 1. System Prompt
Edit the main instructions that define how the LLM should behave:

```yaml
system:
  content: |
    You are an expert at extracting structured knowledge triples...
    
    Rules:
    1. Extract factual relationships only
    2. Use consistent predicates
    # Add your custom rules here
```

### 2. Message Type Prompts
Customize prompts for different message types (question, strategy, analysis, etc.):

```yaml
templates:
  question:
    instruction: |
      Extract question triples from these Discord messages.
      
      Focus on: {your_focus_areas}
      
      Messages:
      {message_text}
      
      Extract triples as JSON array:
```

### 3. Confidence Scores
Adjust confidence levels for different extraction types:

```yaml
config:
  confidence_scores:
    question: 0.90  # Higher confidence for questions
    analysis: 0.75  # Lower confidence for complex analysis
```

### 4. Expected Predicates
Define what predicates each message type should produce:

```yaml
config:
  predicates:
    question: ["asks_about", "inquires_about"]
    strategy: ["recommends", "suggests", "proposes"]
```

## 🔧 Advanced Usage

### Environment-Specific Prompts
Create different prompt files for different environments:

```bash
# Development prompts (more verbose)
python extractor_llm.py input.jsonl output.jsonl --config prompts_dev.yaml

# Production prompts (optimized)  
python extractor_llm.py input.jsonl output.jsonl --config prompts_prod.yaml
```

### A/B Testing Prompts
Compare different prompt strategies:

```bash
# Version A
python extractor_llm.py input.jsonl output_a.jsonl --config prompts_v1.yaml

# Version B  
python extractor_llm.py input.jsonl output_b.jsonl --config prompts_v2.yaml

# Compare results in evaluation app
```

## 🐛 Troubleshooting

### YAML Syntax Errors
```bash
# Test YAML syntax
python -c "import yaml; print(yaml.safe_load(open('prompts.yaml')))"
```

### Missing Keys
The system will log errors if required keys are missing from the YAML file.

### Template Variables
Ensure placeholders like `{message_text}` match exactly in your templates.

## 📚 Example Customizations

### Financial Focus
```yaml
system:
  content: |
    You specialize in financial Discord conversations.
    Focus on trading strategies, market analysis, and investment advice.
```

### Crypto Focus  
```yaml
templates:
  strategy:
    instruction: |
      Extract crypto trading strategies and DeFi recommendations.
      
      Focus on: protocols, yield farming, trading pairs
```

### Higher Precision
```yaml
config:
  confidence_scores:
    question: 0.95
    strategy: 0.92
    analysis: 0.90
```

## 🔄 Migration from Hardcoded Prompts

The YAML configuration maintains compatibility with the original hardcoded prompts. All existing functionality works unchanged, but you can now:

1. **Modify prompts** without code changes
2. **Version control** prompt changes separately
3. **A/B test** different prompt strategies
4. **Environment-specific** prompt tuning
5. **Team collaboration** on prompt engineering

---

**Happy prompt engineering! 🎯**