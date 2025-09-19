#!/usr/bin/env python3

import time
import sys
import os
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import openai
import re
import argparse
import threading

class GPUMonitor:
    """Monitor GPU memory usage during tests."""
    
    def __init__(self):
        self.monitoring = False
        self.max_memory_used = 0
        self.memory_samples = []
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start monitoring GPU memory in background."""
        self.monitoring = True
        self.max_memory_used = 0
        self.memory_samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring and return statistics."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        if self.memory_samples:
            avg_memory = sum(self.memory_samples) / len(self.memory_samples)
            return {
                "max_memory_mb": self.max_memory_used,
                "avg_memory_mb": avg_memory,
                "samples": len(self.memory_samples)
            }
        return None
    
    def _monitor_loop(self):
        """Background loop to sample GPU memory."""
        while self.monitoring:
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=1
                )
                if result.returncode == 0:
                    memory_mb = int(result.stdout.strip().split('\n')[0])
                    self.memory_samples.append(memory_mb)
                    self.max_memory_used = max(self.max_memory_used, memory_mb)
            except:
                pass
            time.sleep(0.5)  # Sample every 500ms

class AdvancedGPUBenchmark:
    """Advanced GPU benchmark with configurable context lengths."""
    
    def __init__(self, gpu_name, model_name, base_url="http://localhost:11434/v1/", api_key="ollama"):
        self.gpu_name = gpu_name
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.client = openai.Client(base_url=base_url, api_key=api_key)
        self.gpu_monitor = GPUMonitor()
        
        # Test parameters
        self.temperature = 0.7
        self.top_p = 0.8
        self.max_tokens = 2000
        self.seed = 1000
        self.cooling_time = 10
        
        # System prompts to avoid caching
        self.system_prompts = [
            "You are a helpful assistant. Provide a summary and detailed analysis. /no_think",
            "Provide a summary and detailed analysis. You are a helpful assistant. /no_think",
        ]
        
        # Create report filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_gpu = re.sub(r"\W", "_", gpu_name)
        safe_model = re.sub(r"\W", "_", model_name)
        self.report_file = f"report_advanced_{safe_gpu}_{safe_model}_{timestamp}.json"
        self.results = []
    
    def get_gpu_info(self):
        """Get detailed GPU information."""
        try:
            result = subprocess.run([
                "nvidia-smi", 
                "--query-gpu=name,memory.total,memory.free,temperature.gpu,power.draw",
                "--format=csv,noheader"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                info = result.stdout.strip().split(', ')
                return {
                    "name": info[0],
                    "total_memory_mb": int(info[1].replace(' MiB', '')),
                    "free_memory_mb": int(info[2].replace(' MiB', '')),
                    "temperature": int(info[3]) if len(info) > 3 else None,
                    "power_draw": info[4] if len(info) > 4 else None
                }
        except:
            pass
        return None
    
    def test_context_length(self, prompt_file, context_label):
        """Test a specific context length."""
        print(f"\n{'='*60}")
        print(f"Testing {context_label} context on {self.gpu_name}")
        print(f"Model: {self.model_name}")
        print(f"{'='*60}")
        
        # Load prompt
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_text = f.read()
        
        word_count = len(prompt_text.split())
        estimated_tokens = int(word_count * 1.33)
        
        print(f"Prompt: {word_count:,} words (~{estimated_tokens:,} tokens)")
        print(f"File: {prompt_file}")
        
        messages = [
            {"role": "system", "content": self.system_prompts[0]},
            {"role": "user", "content": prompt_text}
        ]
        
        # Warm up
        print("\nWarming up...", end="", flush=True)
        try:
            self._send_request(messages, change_system=False)
            print(" Done")
        except Exception as e:
            print(f" Warning: {e}")
        
        # Start GPU monitoring
        self.gpu_monitor.start_monitoring()
        
        # Run actual test
        print("Running benchmark...", end="", flush=True)
        start_time = time.time()
        
        try:
            stats = self._send_request(messages, change_system=True)
            duration = time.time() - start_time
            
            # Stop monitoring and get stats
            memory_stats = self.gpu_monitor.stop_monitoring()
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "gpu": self.gpu_name,
                "model": self.model_name,
                "context_label": context_label,
                "prompt_file": str(prompt_file),
                "word_count": word_count,
                "estimated_tokens": estimated_tokens,
                "prompt_tokens": stats["prompt_tokens"],
                "prompt_speed": stats["prompt_speed"],
                "ttft": stats["ttft"],
                "completion_tokens": stats["completion_tokens"],
                "completion_speed": stats["completion_speed"],
                "total_duration": duration,
                "memory_stats": memory_stats,
                "success": True,
                "error": None
            }
            
            print(" Success!")
            self._print_results(result)
            
        except Exception as e:
            print(f" Failed: {e}")
            result = {
                "timestamp": datetime.now().isoformat(),
                "gpu": self.gpu_name,
                "model": self.model_name,
                "context_label": context_label,
                "prompt_file": str(prompt_file),
                "word_count": word_count,
                "estimated_tokens": estimated_tokens,
                "success": False,
                "error": str(e)
            }
        
        self.results.append(result)
        self._save_results()
        
        return result
    
    def _send_request(self, messages, change_system=True):
        """Send request to model."""
        if change_system:
            # Alternate system prompts to avoid caching
            messages[0]["content"] = (
                self.system_prompts[0]
                if messages[0]["content"] != self.system_prompts[0]
                else self.system_prompts[1]
            )
        
        ttft = 0
        start_time = time.time()
        
        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            seed=self.seed,
            stream=True,
            stream_options={"include_usage": True}
        )
        
        for event in stream:
            if ttft == 0:
                ttft = time.time() - start_time
        
        duration = time.time() - start_time
        
        # Handle different response formats
        if hasattr(event, 'usage'):
            prompt_tokens = event.usage.prompt_tokens if hasattr(event.usage, 'prompt_tokens') else 0
            completion_tokens = event.usage.completion_tokens if hasattr(event.usage, 'completion_tokens') else 0
        else:
            # Fallback estimates
            prompt_tokens = len(str(messages[-1]["content"]).split())
            completion_tokens = self.max_tokens
        
        prompt_speed = prompt_tokens / ttft if ttft > 0 else 0
        completion_speed = completion_tokens / (duration - ttft) if (duration - ttft) > 0 else 0
        
        return {
            "prompt_tokens": prompt_tokens,
            "prompt_speed": prompt_speed,
            "ttft": ttft,
            "completion_tokens": completion_tokens,
            "completion_speed": completion_speed,
            "duration": duration
        }
    
    def _print_results(self, result):
        """Print formatted results."""
        if result["success"]:
            print(f"\n  Prompt Processing:")
            print(f"    Tokens: {result['prompt_tokens']:,}")
            print(f"    Speed: {result['prompt_speed']:.2f} tokens/sec")
            print(f"    TTFT: {result['ttft']:.2f} seconds")
            
            print(f"\n  Generation:")
            print(f"    Tokens: {result['completion_tokens']:,}")
            print(f"    Speed: {result['completion_speed']:.2f} tokens/sec")
            
            if result.get("memory_stats"):
                print(f"\n  Memory Usage:")
                print(f"    Peak: {result['memory_stats']['max_memory_mb']:,} MB")
                print(f"    Average: {result['memory_stats']['avg_memory_mb']:.0f} MB")
            
            print(f"\n  Total Duration: {result['total_duration']:.2f} seconds")
    
    def _save_results(self):
        """Save results to JSON file."""
        with open(self.report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✓ Results saved to {self.report_file}")
    
    def run_test_suite(self, test_categories=None):
        """Run a suite of context length tests."""
        context_dir = Path("context_prompts")
        
        if not context_dir.exists():
            print("Error: context_prompts directory not found!")
            print("Run: python generate_large_prompts.py first")
            return
        
        # Default test categories based on GPU memory
        if test_categories is None:
            gpu_info = self.get_gpu_info()
            if gpu_info:
                total_mem_gb = gpu_info["total_memory_mb"] / 1024
                print(f"\nDetected GPU: {gpu_info['name']} ({total_mem_gb:.1f}GB)")
                
                if total_mem_gb >= 70:
                    test_categories = ["small", "medium", "large", "extreme"]
                elif total_mem_gb >= 40:
                    test_categories = ["small", "medium", "large"]
                elif total_mem_gb >= 20:
                    test_categories = ["small", "medium"]
                else:
                    test_categories = ["small"]
            else:
                test_categories = ["small", "medium"]
        
        print(f"\nTest categories: {', '.join(test_categories)}")
        
        # Run tests
        for category in test_categories:
            category_dir = context_dir / category
            if not category_dir.exists():
                continue
            
            prompt_files = sorted(category_dir.glob("prompt_*.txt"))
            
            for prompt_file in prompt_files:
                # Extract context label from filename
                context_label = prompt_file.stem.replace("prompt_", "")
                
                # Run test
                result = self.test_context_length(prompt_file, context_label)
                
                # Cool down between tests
                if self.cooling_time > 0:
                    print(f"\nCooling down for {self.cooling_time} seconds...")
                    time.sleep(self.cooling_time)
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate summary report."""
        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*60}")
        print(f"GPU: {self.gpu_name}")
        print(f"Model: {self.model_name}")
        print(f"Total tests: {len(self.results)}")
        
        successful = [r for r in self.results if r.get("success")]
        failed = [r for r in self.results if not r.get("success")]
        
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        
        if successful:
            print(f"\n{'Context':<10} {'PP Speed':<12} {'TG Speed':<12} {'Peak RAM (MB)':<15}")
            print("-" * 50)
            
            for result in successful:
                context = result["context_label"]
                pp_speed = result["prompt_speed"]
                tg_speed = result["completion_speed"]
                peak_mem = result.get("memory_stats", {}).get("max_memory_mb", "N/A")
                
                if isinstance(peak_mem, (int, float)):
                    peak_mem = f"{peak_mem:,}"
                
                print(f"{context:<10} {pp_speed:<12.2f} {tg_speed:<12.2f} {peak_mem:<15}")
        
        if failed:
            print(f"\nFailed tests:")
            for result in failed:
                print(f"  - {result['context_label']}: {result['error']}")
        
        print(f"\n✓ Full results saved to: {self.report_file}")

def main():
    parser = argparse.ArgumentParser(description="Advanced GPU Benchmark for LLMs")
    parser.add_argument("gpu_name", help="GPU identifier (e.g., RTX4090-48GB)")
    parser.add_argument("model", help="Model name (e.g., qwen2.5-coder:32b)")
    parser.add_argument("--categories", nargs="+", 
                       choices=["small", "medium", "large", "extreme"],
                       help="Context categories to test")
    parser.add_argument("--base-url", default="http://localhost:11434/v1/",
                       help="API base URL")
    parser.add_argument("--cooling", type=int, default=10,
                       help="Cooling time between tests (seconds)")
    
    args = parser.parse_args()
    
    # Create benchmark instance
    benchmark = AdvancedGPUBenchmark(
        gpu_name=args.gpu_name,
        model_name=args.model,
        base_url=args.base_url
    )
    
    benchmark.cooling_time = args.cooling
    
    # Run tests
    benchmark.run_test_suite(test_categories=args.categories)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_advanced_gpu.py <GPU_NAME> <MODEL> [options]")
        print("\nExamples:")
        print("  python test_advanced_gpu.py RTX4090-24GB qwen2.5-coder:32b")
        print("  python test_advanced_gpu.py RTX4090-48GB llama3.1:70b --categories medium large")
        print("\nRun 'python test_advanced_gpu.py -h' for all options")
        sys.exit(1)
    
    main()