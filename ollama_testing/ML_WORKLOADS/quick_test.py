#!/usr/bin/env python3
"""Quick test to verify Ollama connection and model availability"""

import sys
import json
import requests
from datetime import datetime

def test_ollama():
    """Test Ollama connection and list models"""
    
    print("=" * 50)
    print("Ollama Connection Test")
    print("=" * 50)
    
    # Test connection
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            print("✓ Ollama server is running")
            models = response.json().get("models", [])
            
            print(f"\nFound {len(models)} models:")
            print("-" * 30)
            
            for model in models:
                name = model.get("name", "unknown")
                size = model.get("size", 0) / (1024**3)  # Convert to GB
                details = model.get("details", {})
                param_size = details.get("parameter_size", "unknown")
                
                print(f"  • {name}")
                print(f"    Size: {size:.1f} GB, Parameters: {param_size}")
            
            return True
        else:
            print("✗ Ollama server responded with error")
            return False
            
    except requests.ConnectionError:
        print("✗ Cannot connect to Ollama server at localhost:11434")
        print("\nTo start Ollama:")
        print("  1. Open a new terminal")
        print("  2. Run: ollama serve")
        print("  3. Wait for it to start")
        print("  4. Run this test again")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_openai_api():
    """Test OpenAI-compatible API endpoint"""
    
    print("\n" + "=" * 50)
    print("OpenAI API Compatibility Test")
    print("=" * 50)
    
    try:
        # Test the OpenAI-compatible endpoint
        import openai
        
        client = openai.Client(
            base_url="http://localhost:11434/v1/",
            api_key="ollama"
        )
        
        # Try to list models via OpenAI API
        response = requests.get(
            "http://localhost:11434/v1/models",
            headers={"Authorization": "Bearer ollama"}
        )
        
        if response.status_code == 200:
            print("✓ OpenAI-compatible API is available")
            return True
        else:
            print("✗ OpenAI API endpoint not responding correctly")
            return False
            
    except Exception as e:
        print(f"⚠ OpenAI API test inconclusive: {e}")
        return False


def test_gpu():
    """Check GPU status"""
    
    print("\n" + "=" * 50)
    print("GPU Status")
    print("=" * 50)
    
    import subprocess
    
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ NVIDIA GPU detected:")
            for line in result.stdout.strip().split('\n'):
                parts = line.split(', ')
                if len(parts) == 3:
                    name = parts[0]
                    mem_used = parts[1]
                    mem_total = parts[2]
                    print(f"  • {name}")
                    print(f"    Memory: {mem_used} / {mem_total}")
        else:
            print("✗ Could not query GPU")
            
    except FileNotFoundError:
        print("✗ nvidia-smi not found - NVIDIA drivers may not be installed")
    except Exception as e:
        print(f"✗ Error checking GPU: {e}")


def quick_benchmark():
    """Run a very quick benchmark"""
    
    print("\n" + "=" * 50)
    print("Quick Benchmark Test")
    print("=" * 50)
    
    try:
        import openai
        import time
        
        # Get first available model
        response = requests.get("http://localhost:11434/api/tags")
        models = response.json().get("models", [])
        
        if not models:
            print("✗ No models available for testing")
            return
        
        # Use the smallest model for quick test
        model_name = min(models, key=lambda x: x.get("size", float('inf')))["name"]
        print(f"Testing with model: {model_name}")
        
        client = openai.Client(
            base_url="http://localhost:11434/v1/",
            api_key="ollama"
        )
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'test complete' and nothing else."}
        ]
        
        print("Sending test prompt...")
        start_time = time.time()
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=10,
                stream=False
            )
            
            duration = time.time() - start_time
            print(f"✓ Response received in {duration:.2f} seconds")
            
        except Exception as e:
            print(f"✗ Benchmark failed: {e}")
            print("\nNote: Ollama's OpenAI compatibility may vary by version")
            
    except Exception as e:
        print(f"✗ Could not run benchmark: {e}")


def main():
    print(f"Test started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    ollama_ok = test_ollama()
    
    if ollama_ok:
        test_openai_api()
        test_gpu()
        quick_benchmark()
    
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    if ollama_ok:
        print("✓ System is ready for GPU benchmarking")
        print("\nNext steps:")
        print("1. Load a model: ./model_selector.sh")
        print("2. Run benchmarks: ./run_gpu_benchmark.sh")
    else:
        print("✗ Please fix the issues above before running benchmarks")


if __name__ == "__main__":
    main()