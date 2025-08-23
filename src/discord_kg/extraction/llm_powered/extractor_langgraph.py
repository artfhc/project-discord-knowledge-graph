"""
LangGraph-based Discord Knowledge Graph Triple Extractor.

This is the main entry point for the redesigned extraction system using LangGraph
for better workflow orchestration, error handling, and maintainability.

Usage:
    python extractor_langgraph.py input.jsonl output.jsonl --provider openai
    python extractor_langgraph.py input.jsonl output.jsonl --provider claude --model claude-3-sonnet-20240229
"""

import sys
import os
import argparse
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    # Try relative imports first (when used as package)
    from .workflow import ExtractionWorkflow, run_extraction_pipeline
    from .config import ConfigManager
    from .workflow_state import NumpyEncoder
    from .enable_recording import enable_recording_in_extractor_langgraph
    from .llm_recorder import get_call_stats, is_recording_enabled
except ImportError:
    # Fall back to direct imports (when running as script)
    from workflow import ExtractionWorkflow, run_extraction_pipeline
    from config import ConfigManager
    from workflow_state import NumpyEncoder
    from enable_recording import enable_recording_in_extractor_langgraph
    from llm_recorder import get_call_stats, is_recording_enabled


def setup_recording_if_enabled() -> Optional[str]:
    """Setup LLM call recording if enabled via environment variable."""
    
    # Check if recording is enabled
    recording_enabled = os.getenv("ENABLE_LLM_RECORDING", "false").lower() in ["true", "1", "yes"]
    
    if not recording_enabled:
        return None
    
    # Get experiment name from environment or generate default
    experiment_name = os.getenv("LLM_EXPERIMENT_NAME")
    if not experiment_name:
        from datetime import datetime
        experiment_name = f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Enable recording
        success = enable_recording_in_extractor_langgraph(experiment_name)
        if success:
            return experiment_name
        else:
            print("⚠️  Failed to enable LLM recording")
            return None
    except Exception as e:
        print(f"⚠️  Error setting up LLM recording: {e}")
        return None


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Setup logging configuration."""
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ] + ([logging.FileHandler(log_file)] if log_file else [])
    )
    
    # Set specific loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)  # Reduce HTTP client noise
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def validate_environment(provider: str) -> bool:
    """Validate that required environment variables and dependencies are available."""
    
    # Check API keys
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ Error: OPENAI_API_KEY environment variable not set")
            print("   Set it with: export OPENAI_API_KEY=your_key_here")
            return False
        
        try:
            import openai
        except ImportError:
            print("❌ Error: OpenAI library not installed")
            print("   Install it with: pip install openai")
            return False
            
    elif provider == "claude":
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
            print("   Set it with: export ANTHROPIC_API_KEY=your_key_here")
            return False
        
        try:
            import anthropic
        except ImportError:
            print("❌ Error: Anthropic library not installed")
            print("   Install it with: pip install anthropic")
            return False
    
    # Check LangGraph
    try:
        import langgraph
    except ImportError:
        print("❌ Error: LangGraph not installed")
        print("   Install it with: pip install langgraph")
        return False
    
    return True


def validate_input_file(input_file: str) -> bool:
    """Validate input file format and content."""
    
    if not Path(input_file).exists():
        print(f"❌ Error: Input file not found: {input_file}")
        return False
    
    try:
        message_count = 0
        with open(input_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        msg = json.loads(line)
                        message_count += 1
                        
                        # Validate required fields
                        required_fields = ['message_id', 'author', 'timestamp']
                        missing_fields = [field for field in required_fields if field not in msg]
                        
                        if missing_fields:
                            print(f"⚠️  Warning: Message on line {line_num} missing fields: {missing_fields}")
                        
                        # Check if it has some text content
                        if not msg.get('clean_text') and not msg.get('text'):
                            print(f"⚠️  Warning: Message on line {line_num} has no text content")
                    
                    except json.JSONDecodeError:
                        print(f"❌ Error: Invalid JSON on line {line_num}")
                        return False
        
        if message_count == 0:
            print("❌ Error: No valid messages found in input file")
            return False
        
        print(f"✅ Input validation passed: {message_count} messages found")
        return True
        
    except Exception as e:
        print(f"❌ Error reading input file: {e}")
        return False


def print_processing_summary(result: Dict[str, Any]) -> None:
    """Print a formatted processing summary."""
    
    if result["status"] != "success":
        print(f"\n❌ Processing failed: {result.get('error', 'Unknown error')}")
        return
    
    summary = result["processing_summary"]
    cost = result["cost_summary"]
    
    print(f"\n✅ Processing completed successfully!")
    print(f"📊 Processing Summary:")
    print(f"   • Total messages processed: {summary['total_messages']}")
    print(f"   • Total triples extracted: {summary['total_triples']}")
    print(f"   • Processing time: {summary['processing_time_seconds']}s")
    
    print(f"\n📋 Message Classification:")
    for msg_type, count in summary.get("message_classification", {}).items():
        print(f"   • {msg_type.title()}: {count}")
    
    print(f"\n🔗 Extraction Results:")
    for msg_type, info in summary.get("extraction_results", {}).items():
        status_emoji = "✅" if info["status"] == "completed" else "⚠️"
        print(f"   • {msg_type.title()}: {status_emoji} {info['triples_extracted']} triples from {info['messages_processed']} messages")
    
    qa_info = summary.get("qa_linking", {})
    qa_emoji = "✅" if qa_info["status"] == "completed" else "⏭️" if qa_info["status"] == "skipped" else "⚠️"
    print(f"   • Q&A Linking: {qa_emoji} {qa_info['links_created']} links created")
    
    print(f"\n💰 Cost Summary:")
    print(f"   • Total cost: ${cost.get('total_cost_usd', 0):.4f}")
    print(f"   • API calls: {cost.get('total_api_calls', 0)}")
    print(f"   • Total tokens: {cost.get('total_tokens', 0):,}")
    print(f"   • Cost per triple: ${cost.get('cost_per_triple', 0):.4f}")
    
    # Add recording statistics if recording is enabled
    try:
        if is_recording_enabled():
            recording_stats = get_call_stats()
            if recording_stats.get('total_calls', 0) > 0:
                print(f"\n📊 Recording Statistics:")
                print(f"   • LLM calls recorded: {recording_stats.get('total_calls', 0)}")
                print(f"   • Recording success rate: {recording_stats.get('success_rate', 0):.1f}%")
                print(f"   • Avg call duration: {recording_stats.get('avg_duration_seconds', 0):.3f}s")
                print(f"   • Data stored in: bin/llm_evaluation/llm_calls.db")
    except Exception:
        pass  # Silently skip if recording modules not available
    
    if result.get("errors"):
        print(f"\n⚠️  Errors encountered ({len(result['errors'])}):")
        for error in result["errors"][-3:]:  # Show last 3 errors
            print(f"   • {error}")
        if len(result["errors"]) > 3:
            print(f"   • ... and {len(result['errors']) - 3} more errors")


def main():
    """Main CLI entry point."""
    
    parser = argparse.ArgumentParser(
        description='LangGraph-based Discord Knowledge Graph Triple Extractor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extractor_langgraph.py messages.jsonl triples.jsonl --provider openai
  python extractor_langgraph.py messages.jsonl triples.jsonl --provider claude --batch-size 10
  python extractor_langgraph.py messages.jsonl triples.jsonl --provider openai --config custom_prompts.yaml
  python extractor_langgraph.py messages.jsonl triples.jsonl --provider claude --model claude-3-sonnet-20240229 --log-level DEBUG

Environment Variables:
  OPENAI_API_KEY        - Required for OpenAI provider
  ANTHROPIC_API_KEY     - Required for Claude provider
  OPENAI_MODEL          - Override default OpenAI model
  ANTHROPIC_MODEL       - Override default Claude model
  
  LLM Recording:
  ENABLE_LLM_RECORDING  - Set to 'true' to enable comprehensive LLM call recording
  LLM_EXPERIMENT_NAME   - Name for the recording experiment (optional)
        """
    )
    
    # Required arguments
    parser.add_argument('input_file', help='Input JSONL file with classified Discord messages')
    parser.add_argument('output_file', help='Output JSONL file for extracted triples')
    
    # LLM configuration
    parser.add_argument('--provider', choices=['openai', 'claude'], default='openai',
                       help='LLM provider (default: openai)')
    parser.add_argument('--model', help='Specific model name (overrides environment variables)')
    
    # Processing configuration
    parser.add_argument('--batch-size', type=int, default=20,
                       help='Messages per LLM request - smaller for accuracy, larger for efficiency (default: 20)')
    parser.add_argument('--config', help='Path to YAML prompt configuration file')
    
    # Workflow options
    parser.add_argument('--enable-checkpoints', action='store_true',
                       help='Enable workflow checkpointing for resuming failed runs')
    parser.add_argument('--thread-id', help='Thread ID for checkpoint resumption')
    
    # Output options
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
                       help='Logging level (default: INFO)')
    parser.add_argument('--log-file', help='Log to file in addition to console')
    parser.add_argument('--quiet', action='store_true', help='Suppress progress output')
    
    # Validation and testing
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate input and configuration, don\'t process')
    parser.add_argument('--dry-run', action='store_true',
                       help='Validate everything but don\'t make API calls')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    # Print banner
    if not args.quiet:
        print("🤖 LangGraph Discord Knowledge Graph Extractor")
        print("=" * 50)
    
    # Validate environment
    if not validate_environment(args.provider):
        return 1
    
    # Validate input file
    if not validate_input_file(args.input_file):
        return 1
    
    # Validate configuration
    try:
        config_manager = ConfigManager(args.config)
        if not config_manager.validate_config():
            print("❌ Configuration validation failed")
            return 1
        
        if not args.quiet:
            print("✅ Configuration validation passed")
            
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return 1
    
    # Setup LLM call recording if enabled
    recording_experiment = setup_recording_if_enabled()
    if recording_experiment and not args.quiet:
        print(f"📊 LLM recording enabled for experiment: {recording_experiment}")
    
    # Exit if validation only
    if args.validate_only:
        print("✅ Validation completed - all checks passed")
        return 0
    
    # Create workflow
    try:
        workflow = ExtractionWorkflow(
            llm_provider=args.provider,
            llm_model=args.model,
            batch_size=args.batch_size,
            config_path=args.config,
            enable_checkpoints=args.enable_checkpoints
        )
        
        if not args.quiet:
            print(f"✅ Workflow initialized with {args.provider} provider")
        
    except Exception as e:
        print(f"❌ Failed to initialize workflow: {e}")
        logger.error(f"Workflow initialization failed", exc_info=True)
        return 1
    
    # Dry run check
    if args.dry_run:
        print("✅ Dry run completed - workflow is ready for processing")
        return 0
    
    # Process file
    try:
        if not args.quiet:
            print(f"\n🚀 Starting processing...")
            print(f"   Input: {args.input_file}")
            print(f"   Output: {args.output_file}")
            print(f"   Provider: {args.provider}")
            print(f"   Batch size: {args.batch_size}")
        
        result = run_extraction_pipeline(
            input_file=args.input_file,
            output_file=args.output_file,
            llm_provider=args.provider,
            llm_model=args.model,
            batch_size=args.batch_size,
            config_path=args.config
        )
        
        if not args.quiet:
            print_processing_summary(result)
        
        if result["status"] == "success":
            return 0
        else:
            print(f"\n❌ Processing failed: {result.get('error', 'Unknown error')}")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
        return 130
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.error("Unexpected error during processing", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())