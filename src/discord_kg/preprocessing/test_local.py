#!/usr/bin/env python3
"""
Local testing script for Discord message preprocessing pipeline.
Combines preprocessing and classification steps.
"""

import argparse
import sys
from pathlib import Path

# Add the preprocessing module to path
sys.path.append(str(Path(__file__).parent))

from preprocessor import DiscordPreprocessor
from classifier import DiscordMessageClassifier


def run_full_pipeline(input_file: str, output_file: str = None, 
                     model_name: str = "facebook/bart-large-mnli"):
    """Run the complete preprocessing and classification pipeline"""
    
    if output_file is None:
        output_file = "preprocessed_classified_messages.jsonl"
    
    print("Discord Message Preprocessing Pipeline")
    print("=" * 50)
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Model: {model_name}")
    print()
    
    # Step 1: Preprocessing
    print("Step 1: Preprocessing messages...")
    preprocessor = DiscordPreprocessor()
    preprocessed_messages = preprocessor.process_discord_export(input_file)
    preprocessor.print_stats(preprocessed_messages)
    print()
    
    # Step 2: Classification
    print("Step 2: Classifying messages with TinyBERT...")
    classifier = DiscordMessageClassifier(model_name=model_name)
    
    # Classify each preprocessed message
    for msg in preprocessed_messages:
        if msg.clean_text.strip():
            msg_type, confidence = classifier.classify_message(msg.clean_text)
            msg.type = msg_type
            msg.confidence = confidence
    
    # Print classification stats
    classifier.print_stats(preprocessed_messages)
    print()
    
    # Step 3: Save results
    print("Step 3: Saving results...")
    preprocessor.save_results(preprocessed_messages, output_file)
    
    print("\nPipeline completed successfully!")
    return preprocessed_messages


def main():
    """Main function for testing"""
    parser = argparse.ArgumentParser(
        description="Test Discord message preprocessing pipeline locally"
    )
    parser.add_argument(
        "input_file", 
        help="Path to Discord export JSON file"
    )
    parser.add_argument(
        "--output", "-o", 
        default="preprocessed_classified_messages.jsonl",
        help="Output JSONL file path"
    )
    parser.add_argument(
        "--model", 
        default="facebook/bart-large-mnli",
        help="HuggingFace model name for classification"
    )
    parser.add_argument(
        "--preprocess-only", 
        action="store_true",
        help="Run preprocessing only (skip classification)"
    )
    parser.add_argument(
        "--classify-only", 
        action="store_true",
        help="Run classification only (skip preprocessing)"
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not Path(args.input_file).exists():
        print(f"Error: Input file '{args.input_file}' not found")
        sys.exit(1)
    
    if args.preprocess_only:
        # Run preprocessing only
        print("Running preprocessing only...")
        preprocessor = DiscordPreprocessor()
        messages = preprocessor.process_discord_export(args.input_file)
        preprocessor.save_results(messages, args.output)
        preprocessor.print_stats(messages)
        
    elif args.classify_only:
        # Run classification only (expects preprocessed JSONL input)
        print("Running classification only...")
        classifier = DiscordMessageClassifier(model_name=args.model)
        messages = classifier.process_discord_export(args.input_file)
        classifier.save_results(messages, args.output)
        classifier.print_stats(messages)
        
    else:
        # Run full pipeline
        run_full_pipeline(args.input_file, args.output, args.model)


if __name__ == "__main__":
    main()