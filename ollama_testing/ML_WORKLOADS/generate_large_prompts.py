#!/usr/bin/env python3

import os
import sys
from pathlib import Path
import random
import string
import json

def generate_synthetic_text(target_tokens):
    """Generate synthetic text with approximately target_tokens tokens."""
    # Rough approximation: 1 token ≈ 0.75 words for English text
    target_words = int(target_tokens * 0.75)
    
    # Mix of different text patterns for more realistic testing
    patterns = [
        "The quick brown fox jumps over the lazy dog.",
        "In the realm of artificial intelligence and machine learning,",
        "Data processing involves complex algorithms that analyze patterns,",
        "System performance metrics indicate optimal resource utilization,",
        "Advanced neural networks demonstrate remarkable capabilities in understanding,",
        "Memory bandwidth limitations affect computational throughput significantly,",
        "Optimization techniques improve model inference speed dramatically,",
        "Hardware acceleration enables faster processing of large datasets,",
        "Distributed computing architectures scale horizontally for better performance,",
        "Cache hierarchies play a crucial role in reducing memory latency,",
    ]
    
    # Add some variety with technical terms
    tech_terms = [
        "GPU", "VRAM", "tensor", "matrix", "kernel", "bandwidth", "latency",
        "throughput", "pipeline", "cache", "buffer", "memory", "compute",
        "parallel", "sequential", "optimization", "inference", "training",
        "quantization", "precision", "floating-point", "integer", "vector"
    ]
    
    words = []
    word_count = 0
    
    while word_count < target_words:
        # Mix different types of content
        choice = random.random()
        
        if choice < 0.6:
            # Use pattern sentences
            sentence = random.choice(patterns)
            words.append(sentence)
            word_count += len(sentence.split())
        elif choice < 0.8:
            # Generate technical paragraph
            num_terms = random.randint(5, 15)
            technical_sentence = "The " + " ".join(random.choices(tech_terms, k=num_terms)) + " operations require careful consideration."
            words.append(technical_sentence)
            word_count += len(technical_sentence.split())
        else:
            # Add some numbers and data
            data_line = f"Benchmark result {random.randint(1, 1000)}: {random.uniform(10.0, 1000.0):.2f} tokens/sec at {random.randint(50, 100)}% utilization."
            words.append(data_line)
            word_count += len(data_line.split())
    
    return " ".join(words)

def create_context_length_prompts():
    """Create prompts for various context lengths suitable for GPU testing."""
    
    # Define context lengths to test (in tokens)
    # These are designed to test different VRAM capacities
    context_configs = {
        "small": [
            (1024, "1k"),
            (2048, "2k"),
            (4096, "4k"),
            (8192, "8k"),
        ],
        "medium": [
            (16384, "16k"),
            (32768, "32k"),
            (49152, "48k"),
            (65536, "64k"),
        ],
        "large": [
            (98304, "96k"),
            (131072, "128k"),
            (196608, "192k"),
            (262144, "256k"),
        ],
        "extreme": [
            (393216, "384k"),
            (524288, "512k"),
            (786432, "768k"),
            (1048576, "1M"),
        ]
    }
    
    # Create directories
    base_dir = Path("context_prompts")
    base_dir.mkdir(exist_ok=True)
    
    stats = []
    
    for category, configs in context_configs.items():
        category_dir = base_dir / category
        category_dir.mkdir(exist_ok=True)
        
        print(f"\nGenerating {category} context prompts:")
        
        for token_count, label in configs:
            filename = category_dir / f"prompt_{label}.txt"
            
            # Check if we should generate this file
            expected_size_mb = token_count * 4 / 1024 / 1024  # Rough estimate
            
            if expected_size_mb > 100:
                print(f"  Skipping {label} ({token_count:,} tokens) - would be ~{expected_size_mb:.1f}MB")
                continue
            
            print(f"  Generating {label} ({token_count:,} tokens)...", end="", flush=True)
            
            text = generate_synthetic_text(token_count)
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(text)
            
            actual_words = len(text.split())
            actual_tokens_est = int(actual_words * 1.33)
            file_size = os.path.getsize(filename)
            
            stats.append({
                "category": category,
                "label": label,
                "target_tokens": token_count,
                "actual_words": actual_words,
                "estimated_tokens": actual_tokens_est,
                "file_size_mb": file_size / 1024 / 1024,
                "filename": str(filename)
            })
            
            print(f" Done ({actual_words:,} words, {file_size/1024/1024:.2f}MB)")
    
    # Save statistics
    stats_file = base_dir / "prompt_stats.json"
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n✓ Created {len(stats)} prompt files in {base_dir}/")
    print(f"✓ Statistics saved to {stats_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("CONTEXT LENGTH TEST PROMPTS SUMMARY")
    print("="*60)
    
    for category in context_configs.keys():
        category_stats = [s for s in stats if s["category"] == category]
        if category_stats:
            print(f"\n{category.upper()} ({len(category_stats)} files):")
            for stat in category_stats:
                print(f"  {stat['label']:>6}: {stat['estimated_tokens']:>8,} tokens ({stat['file_size_mb']:>6.2f}MB)")
    
    print("\n" + "="*60)
    print("RECOMMENDED TESTING PROGRESSION:")
    print("="*60)
    print("\n24GB VRAM GPUs:")
    print("  - Test: small + medium/16k, 32k")
    print("  - Max context: ~32-48k tokens (model dependent)")
    
    print("\n48GB VRAM GPUs:")
    print("  - Test: small + medium + large/96k, 128k")
    print("  - Max context: ~128-192k tokens (model dependent)")
    
    print("\n80GB+ VRAM GPUs:")
    print("  - Test: all categories")
    print("  - Max context: 256k+ tokens")
    
    print("\nNote: Actual capacity depends on model size and quantization!")

if __name__ == "__main__":
    create_context_length_prompts()