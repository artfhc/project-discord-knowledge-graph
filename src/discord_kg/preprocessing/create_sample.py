#!/usr/bin/env python3
"""
Create a sample of Discord messages for testing.
Preserves the JSON structure while reducing the number of messages.
"""

import json
import argparse
import random


def create_sample(input_file: str, output_file: str, sample_size: int = 1000, random_sample: bool = False):
    """Create a sample from Discord export JSON"""
    
    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_messages = data.get("messages", [])
    total_messages = len(original_messages)
    
    print(f"Original file has {total_messages} messages")
    
    if sample_size >= total_messages:
        print(f"Sample size ({sample_size}) >= total messages ({total_messages}), using all messages")
        sample_messages = original_messages
    else:
        if random_sample:
            print(f"Creating random sample of {sample_size} messages...")
            sample_messages = random.sample(original_messages, sample_size)
        else:
            print(f"Creating first {sample_size} messages...")
            sample_messages = original_messages[:sample_size]
    
    # Create new data structure with sampled messages
    sample_data = data.copy()
    sample_data["messages"] = sample_messages
    
    # Save sample
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    print(f"Sample saved to {output_file} with {len(sample_messages)} messages")


def main():
    parser = argparse.ArgumentParser(description="Create a sample from Discord export JSON")
    parser.add_argument("input_file", help="Path to original Discord export JSON")
    parser.add_argument("--output", "-o", default="sample.json", help="Output sample file")
    parser.add_argument("--size", "-s", type=int, default=1000, help="Number of messages to sample")
    parser.add_argument("--random", "-r", action="store_true", help="Use random sampling instead of first N messages")
    
    args = parser.parse_args()
    
    create_sample(args.input_file, args.output, args.size, args.random)


if __name__ == "__main__":
    main()