#!/usr/bin/env python3

import json
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import argparse

class GPUComparisonAnalyzer:
    """Analyze and compare GPU benchmark results."""
    
    def __init__(self):
        self.results_24gb = []
        self.results_48gb = []
        self.comparison_data = {}
    
    def load_results(self, pattern_24gb="*24GB*.json", pattern_48gb="*48GB*.json"):
        """Load benchmark results from JSON files."""
        
        # Load 24GB results
        files_24gb = glob.glob(f"report*{pattern_24gb}")
        for file in files_24gb:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.results_24gb.extend(data)
                    else:
                        self.results_24gb.append(data)
                print(f"Loaded 24GB results from: {file}")
            except Exception as e:
                print(f"Error loading {file}: {e}")
        
        # Load 48GB results
        files_48gb = glob.glob(f"report*{pattern_48gb}")
        for file in files_48gb:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.results_48gb.extend(data)
                    else:
                        self.results_48gb.append(data)
                print(f"Loaded 48GB results from: {file}")
            except Exception as e:
                print(f"Error loading {file}: {e}")
        
        print(f"\nTotal results loaded:")
        print(f"  24GB: {len(self.results_24gb)} tests")
        print(f"  48GB: {len(self.results_48gb)} tests")
    
    def analyze_performance(self):
        """Analyze performance differences between configurations."""
        
        if not self.results_24gb and not self.results_48gb:
            print("No results loaded!")
            return
        
        print("\n" + "="*80)
        print("GPU PERFORMANCE COMPARISON ANALYSIS")
        print("="*80)
        
        # Group results by context size
        contexts_24gb = {}
        contexts_48gb = {}
        
        for result in self.results_24gb:
            if result.get("success"):
                ctx = result.get("context_label", "unknown")
                if ctx not in contexts_24gb:
                    contexts_24gb[ctx] = []
                contexts_24gb[ctx].append(result)
        
        for result in self.results_48gb:
            if result.get("success"):
                ctx = result.get("context_label", "unknown")
                if ctx not in contexts_48gb:
                    contexts_48gb[ctx] = []
                contexts_48gb[ctx].append(result)
        
        # Compare common context sizes
        common_contexts = set(contexts_24gb.keys()) & set(contexts_48gb.keys())
        
        if common_contexts:
            print("\n" + "-"*80)
            print("PERFORMANCE COMPARISON BY CONTEXT SIZE")
            print("-"*80)
            print(f"{'Context':<10} {'Metric':<20} {'24GB':<15} {'48GB':<15} {'Improvement':<15}")
            print("-"*80)
            
            for ctx in sorted(common_contexts):
                # Calculate averages for 24GB
                results_24 = contexts_24gb[ctx]
                avg_pp_24 = np.mean([r["prompt_speed"] for r in results_24])
                avg_tg_24 = np.mean([r["completion_speed"] for r in results_24])
                avg_ttft_24 = np.mean([r["ttft"] for r in results_24])
                
                # Calculate averages for 48GB
                results_48 = contexts_48gb[ctx]
                avg_pp_48 = np.mean([r["prompt_speed"] for r in results_48])
                avg_tg_48 = np.mean([r["completion_speed"] for r in results_48])
                avg_ttft_48 = np.mean([r["ttft"] for r in results_48])
                
                # Calculate improvements
                pp_improvement = ((avg_pp_48 - avg_pp_24) / avg_pp_24) * 100 if avg_pp_24 > 0 else 0
                tg_improvement = ((avg_tg_48 - avg_tg_24) / avg_tg_24) * 100 if avg_tg_24 > 0 else 0
                ttft_improvement = ((avg_ttft_24 - avg_ttft_48) / avg_ttft_24) * 100 if avg_ttft_24 > 0 else 0
                
                print(f"{ctx:<10} {'Prompt Speed (t/s)':<20} {avg_pp_24:<15.2f} {avg_pp_48:<15.2f} {pp_improvement:+14.1f}%")
                print(f"{'':<10} {'Generation (t/s)':<20} {avg_tg_24:<15.2f} {avg_tg_48:<15.2f} {tg_improvement:+14.1f}%")
                print(f"{'':<10} {'TTFT (seconds)':<20} {avg_ttft_24:<15.2f} {avg_ttft_48:<15.2f} {ttft_improvement:+14.1f}%")
                print("-"*80)
                
                # Store for plotting
                self.comparison_data[ctx] = {
                    "pp_24": avg_pp_24, "pp_48": avg_pp_48,
                    "tg_24": avg_tg_24, "tg_48": avg_tg_48,
                    "ttft_24": avg_ttft_24, "ttft_48": avg_ttft_48
                }
        
        # Check for context sizes only available on 48GB
        exclusive_48gb = set(contexts_48gb.keys()) - set(contexts_24gb.keys())
        if exclusive_48gb:
            print("\n" + "-"*80)
            print("CONTEXT SIZES ONLY ACHIEVABLE WITH 48GB")
            print("-"*80)
            print(f"{'Context':<10} {'Prompt Tokens':<15} {'PP Speed':<15} {'TG Speed':<15}")
            print("-"*80)
            
            for ctx in sorted(exclusive_48gb):
                results = contexts_48gb[ctx]
                avg_tokens = np.mean([r["prompt_tokens"] for r in results])
                avg_pp = np.mean([r["prompt_speed"] for r in results])
                avg_tg = np.mean([r["completion_speed"] for r in results])
                
                print(f"{ctx:<10} {avg_tokens:<15.0f} {avg_pp:<15.2f} {avg_tg:<15.2f}")
        
        # Memory usage comparison
        self._analyze_memory_usage()
        
        # Bandwidth analysis
        self._analyze_bandwidth()
    
    def _analyze_memory_usage(self):
        """Analyze memory usage patterns."""
        print("\n" + "-"*80)
        print("MEMORY USAGE ANALYSIS")
        print("-"*80)
        
        # Extract memory stats
        memory_24gb = []
        memory_48gb = []
        
        for result in self.results_24gb:
            if result.get("success") and result.get("memory_stats"):
                memory_24gb.append({
                    "context": result["context_label"],
                    "tokens": result["prompt_tokens"],
                    "peak_mb": result["memory_stats"]["max_memory_mb"]
                })
        
        for result in self.results_48gb:
            if result.get("success") and result.get("memory_stats"):
                memory_48gb.append({
                    "context": result["context_label"],
                    "tokens": result["prompt_tokens"],
                    "peak_mb": result["memory_stats"]["max_memory_mb"]
                })
        
        if memory_24gb:
            print("\n24GB Configuration:")
            print(f"  Max memory used: {max(m['peak_mb'] for m in memory_24gb):,} MB")
            print(f"  Avg memory used: {np.mean([m['peak_mb'] for m in memory_24gb]):.0f} MB")
            print(f"  Memory efficiency: {np.mean([m['tokens']/m['peak_mb'] for m in memory_24gb]):.2f} tokens/MB")
        
        if memory_48gb:
            print("\n48GB Configuration:")
            print(f"  Max memory used: {max(m['peak_mb'] for m in memory_48gb):,} MB")
            print(f"  Avg memory used: {np.mean([m['peak_mb'] for m in memory_48gb]):.0f} MB")
            print(f"  Memory efficiency: {np.mean([m['tokens']/m['peak_mb'] for m in memory_48gb]):.2f} tokens/MB")
    
    def _analyze_bandwidth(self):
        """Estimate memory bandwidth utilization."""
        print("\n" + "-"*80)
        print("BANDWIDTH UTILIZATION ESTIMATE")
        print("-"*80)
        
        # Theoretical bandwidth (rough estimates)
        bandwidth_24gb = 936  # GB/s for RTX 4090
        bandwidth_48gb = 936  # Same for modded 48GB version
        
        print(f"\nTheoretical bandwidth: {bandwidth_24gb} GB/s")
        
        # Calculate effective bandwidth for each configuration
        for results, label, bandwidth in [(self.results_24gb, "24GB", bandwidth_24gb),
                                          (self.results_48gb, "48GB", bandwidth_48gb)]:
            if not results:
                continue
            
            print(f"\n{label} Configuration:")
            
            bandwidths = []
            for result in results:
                if result.get("success"):
                    # Estimate data moved (very rough approximation)
                    # Assumes 2 bytes per parameter for FP16
                    tokens = result["prompt_tokens"] + result["completion_tokens"]
                    duration = result["total_duration"]
                    
                    # Rough estimate: each token requires reading/writing from model weights
                    # Assuming 7B model = 14GB in FP16, each token touches ~10% of weights
                    data_gb = (tokens * 1.4) / 1024  # Very rough estimate
                    
                    if duration > 0:
                        effective_bandwidth = data_gb / duration
                        utilization = (effective_bandwidth / bandwidth) * 100
                        bandwidths.append(utilization)
            
            if bandwidths:
                print(f"  Estimated utilization: {np.mean(bandwidths):.1f}%")
                print(f"  Peak utilization: {max(bandwidths):.1f}%")
    
    def create_plots(self):
        """Create comparison plots."""
        if not self.comparison_data:
            print("\nNo comparison data available for plotting!")
            return
        
        print("\n" + "-"*80)
        print("GENERATING COMPARISON PLOTS")
        print("-"*80)
        
        contexts = sorted(self.comparison_data.keys())
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle("GPU Performance Comparison: 24GB vs 48GB", fontsize=16)
        
        # Plot 1: Prompt Processing Speed
        ax1 = axes[0, 0]
        x = np.arange(len(contexts))
        width = 0.35
        
        pp_24 = [self.comparison_data[c]["pp_24"] for c in contexts]
        pp_48 = [self.comparison_data[c]["pp_48"] for c in contexts]
        
        ax1.bar(x - width/2, pp_24, width, label='24GB', color='blue', alpha=0.7)
        ax1.bar(x + width/2, pp_48, width, label='48GB', color='green', alpha=0.7)
        ax1.set_xlabel('Context Size')
        ax1.set_ylabel('Tokens/Second')
        ax1.set_title('Prompt Processing Speed')
        ax1.set_xticks(x)
        ax1.set_xticklabels(contexts)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Token Generation Speed
        ax2 = axes[0, 1]
        tg_24 = [self.comparison_data[c]["tg_24"] for c in contexts]
        tg_48 = [self.comparison_data[c]["tg_48"] for c in contexts]
        
        ax2.bar(x - width/2, tg_24, width, label='24GB', color='blue', alpha=0.7)
        ax2.bar(x + width/2, tg_48, width, label='48GB', color='green', alpha=0.7)
        ax2.set_xlabel('Context Size')
        ax2.set_ylabel('Tokens/Second')
        ax2.set_title('Token Generation Speed')
        ax2.set_xticks(x)
        ax2.set_xticklabels(contexts)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: TTFT Comparison
        ax3 = axes[1, 0]
        ttft_24 = [self.comparison_data[c]["ttft_24"] for c in contexts]
        ttft_48 = [self.comparison_data[c]["ttft_48"] for c in contexts]
        
        ax3.bar(x - width/2, ttft_24, width, label='24GB', color='red', alpha=0.7)
        ax3.bar(x + width/2, ttft_48, width, label='48GB', color='orange', alpha=0.7)
        ax3.set_xlabel('Context Size')
        ax3.set_ylabel('Seconds')
        ax3.set_title('Time to First Token (Lower is Better)')
        ax3.set_xticks(x)
        ax3.set_xticklabels(contexts)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Speedup Ratio
        ax4 = axes[1, 1]
        pp_speedup = [(self.comparison_data[c]["pp_48"] / self.comparison_data[c]["pp_24"] - 1) * 100 
                      for c in contexts]
        tg_speedup = [(self.comparison_data[c]["tg_48"] / self.comparison_data[c]["tg_24"] - 1) * 100 
                      for c in contexts]
        
        ax4.plot(contexts, pp_speedup, 'o-', label='Prompt Processing', linewidth=2, markersize=8)
        ax4.plot(contexts, tg_speedup, 's-', label='Token Generation', linewidth=2, markersize=8)
        ax4.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax4.set_xlabel('Context Size')
        ax4.set_ylabel('Improvement (%)')
        ax4.set_title('48GB Performance Improvement over 24GB')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_file = f"gpu_comparison_{timestamp}.png"
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        print(f"✓ Plots saved to: {plot_file}")
        
        # Show plot if running interactively
        try:
            plt.show()
        except:
            pass
    
    def generate_report(self):
        """Generate comprehensive comparison report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"gpu_comparison_report_{timestamp}.md"
        
        with open(report_file, 'w') as f:
            f.write("# GPU Performance Comparison Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Executive Summary\n\n")
            
            if self.comparison_data:
                # Calculate overall improvements
                pp_improvements = []
                tg_improvements = []
                
                for ctx in self.comparison_data:
                    pp_24 = self.comparison_data[ctx]["pp_24"]
                    pp_48 = self.comparison_data[ctx]["pp_48"]
                    tg_24 = self.comparison_data[ctx]["tg_24"]
                    tg_48 = self.comparison_data[ctx]["tg_48"]
                    
                    if pp_24 > 0:
                        pp_improvements.append((pp_48 - pp_24) / pp_24 * 100)
                    if tg_24 > 0:
                        tg_improvements.append((tg_48 - tg_24) / tg_24 * 100)
                
                if pp_improvements:
                    f.write(f"- **Average Prompt Processing Improvement**: {np.mean(pp_improvements):.1f}%\n")
                if tg_improvements:
                    f.write(f"- **Average Token Generation Improvement**: {np.mean(tg_improvements):.1f}%\n")
                
                f.write("\n## Detailed Performance Metrics\n\n")
                f.write("### Comparison by Context Size\n\n")
                f.write("| Context | Metric | 24GB | 48GB | Improvement |\n")
                f.write("|---------|--------|------|------|-------------|\n")
                
                for ctx in sorted(self.comparison_data.keys()):
                    data = self.comparison_data[ctx]
                    pp_imp = ((data["pp_48"] - data["pp_24"]) / data["pp_24"] * 100) if data["pp_24"] > 0 else 0
                    tg_imp = ((data["tg_48"] - data["tg_24"]) / data["tg_24"] * 100) if data["tg_24"] > 0 else 0
                    
                    f.write(f"| {ctx} | Prompt (t/s) | {data['pp_24']:.2f} | {data['pp_48']:.2f} | {pp_imp:+.1f}% |\n")
                    f.write(f"| | Generation (t/s) | {data['tg_24']:.2f} | {data['tg_48']:.2f} | {tg_imp:+.1f}% |\n")
            
            f.write("\n## Recommendations\n\n")
            f.write("### When to use 48GB configuration:\n\n")
            f.write("1. **Large context processing** (>32k tokens)\n")
            f.write("2. **Batch inference** with multiple concurrent requests\n")
            f.write("3. **Large models** (70B+ parameters)\n")
            f.write("4. **Production workloads** requiring consistent performance\n\n")
            
            f.write("### When 24GB is sufficient:\n\n")
            f.write("1. **Small to medium contexts** (<32k tokens)\n")
            f.write("2. **Smaller models** (<40B parameters)\n")
            f.write("3. **Development and testing** environments\n")
            f.write("4. **Cost-sensitive deployments**\n")
        
        print(f"\n✓ Report saved to: {report_file}")

def main():
    parser = argparse.ArgumentParser(description="Analyze GPU benchmark comparisons")
    parser.add_argument("--pattern-24gb", default="*24GB*", help="Pattern for 24GB result files")
    parser.add_argument("--pattern-48gb", default="*48GB*", help="Pattern for 48GB result files")
    parser.add_argument("--no-plots", action="store_true", help="Skip generating plots")
    
    args = parser.parse_args()
    
    analyzer = GPUComparisonAnalyzer()
    
    # Load results
    analyzer.load_results(args.pattern_24gb, args.pattern_48gb)
    
    # Analyze performance
    analyzer.analyze_performance()
    
    # Generate plots
    if not args.no_plots:
        try:
            analyzer.create_plots()
        except ImportError:
            print("\nWarning: matplotlib not installed. Skipping plots.")
            print("Install with: pip install matplotlib")
    
    # Generate report
    analyzer.generate_report()

if __name__ == "__main__":
    main()