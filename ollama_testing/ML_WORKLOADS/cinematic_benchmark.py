#!/usr/bin/env python3
"""
Cinematic GPU Benchmark Dashboard
Real-time visual display for LLM performance testing
"""

import os
import sys
import time
import threading
import queue
import subprocess
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
import openai
import curses
from collections import deque
import signal

# Configuration
base_url = "http://localhost:11434/v1/"
api_key = "ollama"
temperature = 0.7
top_p = 0.8
max_tokens = 2000
seed = 1000

class GPUMonitor:
    """Monitors GPU metrics in real-time"""
    
    def __init__(self):
        self.metrics = {
            'temperature': 0,
            'fan_speed': 0,
            'power_draw': 0,
            'memory_used': 0,
            'memory_total': 0,
            'gpu_utilization': 0,
            'clock_speed': 0,
            'name': 'Unknown GPU'
        }
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        
    def start(self):
        self.thread.start()
        
    def stop(self):
        self.running = False
        
    def _monitor_loop(self):
        while self.running:
            try:
                # Query all metrics at once for efficiency
                result = subprocess.run([
                    'nvidia-smi',
                    '--query-gpu=name,temperature.gpu,fan.speed,power.draw,memory.used,memory.total,utilization.gpu,clocks.current.graphics',
                    '--format=csv,noheader,nounits'
                ], capture_output=True, text=True, timeout=2)
                
                if result.returncode == 0:
                    parts = result.stdout.strip().split(', ')
                    if len(parts) >= 8:
                        self.metrics['name'] = parts[0]
                        self.metrics['temperature'] = int(float(parts[1]))
                        self.metrics['fan_speed'] = int(float(parts[2])) if parts[2] != '[N/A]' else 0
                        self.metrics['power_draw'] = int(float(parts[3])) if parts[3] != '[N/A]' else 0
                        self.metrics['memory_used'] = int(float(parts[4]))
                        self.metrics['memory_total'] = int(float(parts[5]))
                        self.metrics['gpu_utilization'] = int(float(parts[6]))
                        self.metrics['clock_speed'] = int(float(parts[7]))
            except Exception:
                pass
            time.sleep(0.5)  # Update every 500ms

class CinematicBenchmark:
    """Main cinematic benchmark display"""
    
    def __init__(self, gpu_name, model_name):
        self.gpu_name = gpu_name
        self.model_name = model_name
        self.gpu_monitor = GPUMonitor()
        self.client = openai.Client(base_url=base_url, api_key=api_key)
        
        # Performance metrics
        self.current_prompt = ""
        self.current_response = ""
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.ttft = 0.0
        self.tokens_per_sec = 0.0
        self.prompt_speed = 0.0
        
        # History for graphs
        self.temp_history = deque(maxlen=60)
        self.util_history = deque(maxlen=60)
        self.tps_history = deque(maxlen=30)
        
        # Colors
        self.colors = {}
        self.stdscr = None
        self.running = True
        
    def init_colors(self):
        """Initialize color pairs for the display"""
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(1, curses.COLOR_GREEN, -1)   # Success/Good
        curses.init_pair(2, curses.COLOR_YELLOW, -1)  # Warning
        curses.init_pair(3, curses.COLOR_RED, -1)     # Error/Hot
        curses.init_pair(4, curses.COLOR_CYAN, -1)    # Info
        curses.init_pair(5, curses.COLOR_MAGENTA, -1) # Accent
        curses.init_pair(6, curses.COLOR_WHITE, -1)   # Normal bright
        curses.init_pair(7, curses.COLOR_BLUE, -1)    # Frame
        
        self.colors = {
            'success': curses.color_pair(1),
            'warning': curses.color_pair(2),
            'error': curses.color_pair(3),
            'info': curses.color_pair(4),
            'accent': curses.color_pair(5),
            'bright': curses.color_pair(6),
            'frame': curses.color_pair(7),
        }
        
    def draw_box(self, y, x, h, w, title="", color=None):
        """Draw a box with optional title"""
        if color is None:
            color = self.colors['frame']
            
        # Draw corners
        self.stdscr.addstr(y, x, "╔", color)
        self.stdscr.addstr(y, x + w - 1, "╗", color)
        self.stdscr.addstr(y + h - 1, x, "╚", color)
        self.stdscr.addstr(y + h - 1, x + w - 1, "╝", color)
        
        # Draw horizontal lines
        for i in range(x + 1, x + w - 1):
            self.stdscr.addstr(y, i, "═", color)
            self.stdscr.addstr(y + h - 1, i, "═", color)
            
        # Draw vertical lines
        for i in range(y + 1, y + h - 1):
            self.stdscr.addstr(i, x, "║", color)
            self.stdscr.addstr(i, x + w - 1, "║", color)
            
        # Add title if provided
        if title:
            title_str = f" {title} "
            title_x = x + (w - len(title_str)) // 2
            self.stdscr.addstr(y, title_x, title_str, color | curses.A_BOLD)
            
    def draw_progress_bar(self, y, x, width, value, max_val, label="", color=None):
        """Draw a progress bar"""
        if color is None:
            color = self.colors['success']
            
        if max_val == 0:
            percentage = 0
        else:
            percentage = min(100, int((value / max_val) * 100))
            
        filled = int((width - 2) * (percentage / 100))
        
        # Draw the bar
        self.stdscr.addstr(y, x, "[", self.colors['frame'])
        for i in range(width - 2):
            if i < filled:
                self.stdscr.addstr(y, x + 1 + i, "█", color)
            else:
                self.stdscr.addstr(y, x + 1 + i, "░", curses.A_DIM)
        self.stdscr.addstr(y, x + width - 1, "]", self.colors['frame'])
        
        # Add label
        if label:
            label_str = f" {label}: {percentage}%"
            if x + width + len(label_str) < curses.COLS:
                self.stdscr.addstr(y, x + width + 1, label_str, self.colors['info'])
                
    def draw_sparkline(self, y, x, width, data, label=""):
        """Draw a sparkline graph"""
        if not data:
            return
            
        # Sparkline characters
        sparks = " ▁▂▃▄▅▆▇█"
        
        if len(data) > 0:
            min_val = min(data)
            max_val = max(data)
            range_val = max_val - min_val if max_val != min_val else 1
            
            # Sample data if too long
            if len(data) > width:
                step = len(data) / width
                sampled = [data[int(i * step)] for i in range(width)]
            else:
                sampled = list(data)
                
            # Draw the sparkline
            for i, val in enumerate(sampled):
                if i < width:
                    normalized = (val - min_val) / range_val
                    spark_idx = int(normalized * (len(sparks) - 1))
                    color = self.colors['success']
                    if normalized > 0.8:
                        color = self.colors['error']
                    elif normalized > 0.6:
                        color = self.colors['warning']
                    self.stdscr.addstr(y, x + i, sparks[spark_idx], color)
                    
        # Add label
        if label and x + width + 2 < curses.COLS:
            self.stdscr.addstr(y, x + width + 2, label, self.colors['info'])
            
    def format_response_preview(self, text, max_lines=8, max_width=70):
        """Format response text for preview window"""
        if not text:
            return ["Waiting for response..."]
            
        # Clean and wrap text
        lines = []
        words = text.split()
        current_line = ""
        
        for word in words:
            if len(current_line) + len(word) + 1 <= max_width:
                current_line = current_line + " " + word if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
                
            if len(lines) >= max_lines - 1:
                break
                
        if current_line and len(lines) < max_lines:
            lines.append(current_line)
            
        if len(words) > len(" ".join(lines).split()):
            lines.append("...")
            
        return lines
        
    def draw_dashboard(self):
        """Draw the main dashboard"""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Title bar
        title = "╔════ GPU BENCHMARK CINEMATIC DASHBOARD ════╗"
        subtitle = f"Testing {self.model_name} on {self.gpu_name}"
        title_x = (width - len(title)) // 2
        subtitle_x = (width - len(subtitle)) // 2
        
        self.stdscr.addstr(0, title_x, title, self.colors['accent'] | curses.A_BOLD)
        self.stdscr.addstr(1, subtitle_x, subtitle, self.colors['info'])
        
        # GPU Metrics Panel (Top Left)
        gpu_box_y, gpu_box_x = 3, 2
        gpu_box_h, gpu_box_w = 12, 45
        self.draw_box(gpu_box_y, gpu_box_x, gpu_box_h, gpu_box_w, "GPU METRICS", self.colors['success'])
        
        metrics = self.gpu_monitor.metrics
        y_offset = gpu_box_y + 2
        
        # GPU Name
        self.stdscr.addstr(y_offset, gpu_box_x + 2, f"GPU: {metrics['name'][:35]}", self.colors['bright'])
        y_offset += 2
        
        # Temperature with color coding
        temp_color = self.colors['success']
        if metrics['temperature'] > 80:
            temp_color = self.colors['error']
        elif metrics['temperature'] > 70:
            temp_color = self.colors['warning']
        self.stdscr.addstr(y_offset, gpu_box_x + 2, f"Temp: {metrics['temperature']}°C", temp_color)
        self.stdscr.addstr(y_offset, gpu_box_x + 20, f"Fan: {metrics['fan_speed']}%", self.colors['info'])
        y_offset += 1
        
        # Power and Clock
        self.stdscr.addstr(y_offset, gpu_box_x + 2, f"Power: {metrics['power_draw']}W", self.colors['info'])
        self.stdscr.addstr(y_offset, gpu_box_x + 20, f"Clock: {metrics['clock_speed']}MHz", self.colors['info'])
        y_offset += 2
        
        # Memory usage bar
        mem_percent = (metrics['memory_used'] / metrics['memory_total'] * 100) if metrics['memory_total'] > 0 else 0
        self.stdscr.addstr(y_offset, gpu_box_x + 2, "VRAM:", self.colors['bright'])
        self.draw_progress_bar(y_offset, gpu_box_x + 8, 30, metrics['memory_used'], metrics['memory_total'])
        y_offset += 1
        self.stdscr.addstr(y_offset, gpu_box_x + 8, f"{metrics['memory_used']}MB / {metrics['memory_total']}MB", self.colors['info'])
        y_offset += 2
        
        # GPU Utilization bar
        self.stdscr.addstr(y_offset, gpu_box_x + 2, "Load:", self.colors['bright'])
        util_color = self.colors['success']
        if metrics['gpu_utilization'] > 90:
            util_color = self.colors['error']
        elif metrics['gpu_utilization'] > 70:
            util_color = self.colors['warning']
        self.draw_progress_bar(y_offset, gpu_box_x + 8, 30, metrics['gpu_utilization'], 100, color=util_color)
        
        # Performance Metrics Panel (Top Right)
        perf_box_y, perf_box_x = 3, 50
        perf_box_h, perf_box_w = 12, 45
        self.draw_box(perf_box_y, perf_box_x, perf_box_h, perf_box_w, "PERFORMANCE", self.colors['accent'])
        
        y_offset = perf_box_y + 2
        self.stdscr.addstr(y_offset, perf_box_x + 2, "━━━ Token Statistics ━━━", self.colors['bright'])
        y_offset += 2
        
        self.stdscr.addstr(y_offset, perf_box_x + 2, f"Prompt Tokens:  {self.prompt_tokens:,}", self.colors['info'])
        y_offset += 1
        self.stdscr.addstr(y_offset, perf_box_x + 2, f"Output Tokens:  {self.completion_tokens:,}", self.colors['info'])
        y_offset += 2
        
        self.stdscr.addstr(y_offset, perf_box_x + 2, "━━━ Speed Metrics ━━━", self.colors['bright'])
        y_offset += 2
        
        # Speed metrics with color coding
        tps_color = self.colors['success']
        if self.tokens_per_sec < 10:
            tps_color = self.colors['error']
        elif self.tokens_per_sec < 30:
            tps_color = self.colors['warning']
            
        self.stdscr.addstr(y_offset, perf_box_x + 2, f"TTFT: {self.ttft:.2f}s", self.colors['info'])
        y_offset += 1
        self.stdscr.addstr(y_offset, perf_box_x + 2, f"Gen Speed: {self.tokens_per_sec:.1f} tok/s", tps_color)
        y_offset += 1
        self.stdscr.addstr(y_offset, perf_box_x + 2, f"Prompt Speed: {self.prompt_speed:.1f} tok/s", self.colors['info'])
        
        # Prompt Preview Panel (Middle Left)
        prompt_box_y, prompt_box_x = 16, 2
        prompt_box_h, prompt_box_w = 10, 45
        self.draw_box(prompt_box_y, prompt_box_x, prompt_box_h, prompt_box_w, "CURRENT PROMPT", self.colors['info'])
        
        # Display prompt preview
        prompt_lines = self.format_response_preview(self.current_prompt, max_lines=7, max_width=40)
        for i, line in enumerate(prompt_lines[:7]):
            if prompt_box_y + 2 + i < prompt_box_y + prompt_box_h - 1:
                self.stdscr.addstr(prompt_box_y + 2 + i, prompt_box_x + 2, line[:40], self.colors['bright'])
                
        # Response Preview Panel (Middle Right)
        resp_box_y, resp_box_x = 16, 50
        resp_box_h, resp_box_w = 10, 45
        self.draw_box(resp_box_y, resp_box_x, resp_box_h, resp_box_w, "MODEL RESPONSE", self.colors['success'])
        
        # Display response preview with typing effect
        response_lines = self.format_response_preview(self.current_response, max_lines=7, max_width=40)
        for i, line in enumerate(response_lines[:7]):
            if resp_box_y + 2 + i < resp_box_y + resp_box_h - 1:
                # Add slight color variation for "typing" effect
                color = self.colors['bright'] if i < len(response_lines) - 1 else self.colors['success']
                self.stdscr.addstr(resp_box_y + 2 + i, resp_box_x + 2, line[:40], color)
                
        # Graph Panel (Bottom)
        graph_box_y, graph_box_x = 27, 2
        graph_box_h, graph_box_w = height - 29, width - 4
        if graph_box_h > 2 and graph_box_w > 10:
            self.draw_box(graph_box_y, graph_box_x, graph_box_h, graph_box_w, "LIVE METRICS", self.colors['frame'])
            
            # Draw sparklines
            if graph_box_h > 4:
                # Temperature history
                self.temp_history.append(metrics['temperature'])
                self.draw_sparkline(graph_box_y + 2, graph_box_x + 2, min(40, graph_box_w - 20), 
                                  self.temp_history, f"Temp: {metrics['temperature']}°C")
                
                # GPU utilization history
                self.util_history.append(metrics['gpu_utilization'])
                self.draw_sparkline(graph_box_y + 3, graph_box_x + 2, min(40, graph_box_w - 20), 
                                  self.util_history, f"Load: {metrics['gpu_utilization']}%")
                
                # Tokens per second history
                if self.tokens_per_sec > 0:
                    self.tps_history.append(self.tokens_per_sec)
                if graph_box_h > 5 and self.tps_history:
                    self.draw_sparkline(graph_box_y + 4, graph_box_x + 2, min(40, graph_box_w - 20), 
                                      self.tps_history, f"Speed: {self.tokens_per_sec:.1f} t/s")
                    
        # Status bar
        status_y = height - 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_text = f" {timestamp} | Press 'q' to quit | Press 's' to skip prompt "
        self.stdscr.addstr(status_y, 0, status_text[:width], self.colors['frame'] | curses.A_REVERSE)
        
        self.stdscr.refresh()
        
    def run_prompt_test(self, prompt_text, prompt_num, total_prompts):
        """Run a single prompt test with visual feedback"""
        self.current_prompt = prompt_text
        self.current_response = ""
        self.prompt_tokens = len(prompt_text.split())  # Rough estimate
        self.completion_tokens = 0
        self.ttft = 0
        self.tokens_per_sec = 0
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt_text}
        ]
        
        start_time = time.time()
        first_token_time = None
        response_chunks = []
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                seed=seed,
                stream=True,
                stream_options={"include_usage": True}
            )
            
            for event in stream:
                if first_token_time is None:
                    first_token_time = time.time()
                    self.ttft = first_token_time - start_time
                    
                # Extract token if available
                if hasattr(event, 'choices') and event.choices:
                    if hasattr(event.choices[0], 'delta') and hasattr(event.choices[0].delta, 'content'):
                        chunk = event.choices[0].delta.content
                        if chunk:
                            response_chunks.append(chunk)
                            self.current_response = "".join(response_chunks)
                            
                # Update metrics
                elapsed = time.time() - start_time
                if first_token_time and elapsed > self.ttft:
                    self.completion_tokens = len("".join(response_chunks).split())
                    self.tokens_per_sec = self.completion_tokens / (elapsed - self.ttft)
                    
                if self.ttft > 0:
                    self.prompt_speed = self.prompt_tokens / self.ttft
                    
                # Update display
                self.draw_dashboard()
                
            # Final metrics
            if hasattr(event, 'usage'):
                self.prompt_tokens = event.usage.prompt_tokens if hasattr(event.usage, 'prompt_tokens') else self.prompt_tokens
                self.completion_tokens = event.usage.completion_tokens if hasattr(event.usage, 'completion_tokens') else self.completion_tokens
                
        except Exception as e:
            self.current_response = f"Error: {str(e)}"
            
    def run(self, stdscr):
        """Main run loop"""
        self.stdscr = stdscr
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)    # Non-blocking input
        stdscr.timeout(100)  # Refresh every 100ms
        
        self.init_colors()
        self.gpu_monitor.start()
        
        # Load prompts
        prompts = self.load_prompts()
        
        try:
            prompt_index = 0
            while self.running and prompt_index < len(prompts):
                # Check for user input
                key = stdscr.getch()
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    prompt_index += 1
                    continue
                    
                # Run test for current prompt
                self.run_prompt_test(prompts[prompt_index], prompt_index + 1, len(prompts))
                
                # Cool down period with visual countdown
                if prompt_index < len(prompts) - 1:
                    for i in range(10, 0, -1):
                        self.draw_dashboard()
                        cooldown_text = f" Cooling down: {i}s | Next prompt: {prompt_index + 2}/{len(prompts)} "
                        y = curses.LINES - 1
                        x = (curses.COLS - len(cooldown_text)) // 2
                        self.stdscr.addstr(y, x, cooldown_text, self.colors['warning'] | curses.A_REVERSE)
                        self.stdscr.refresh()
                        time.sleep(1)
                        
                        key = stdscr.getch()
                        if key == ord('q'):
                            self.running = False
                            break
                        elif key == ord('s'):
                            break
                            
                prompt_index += 1
                
        finally:
            self.gpu_monitor.stop()
            
    def load_prompts(self):
        """Load test prompts"""
        prompts_dir = Path("prompts")
        if prompts_dir.exists():
            files = sorted(prompts_dir.glob("*.txt"), key=lambda x: int(x.stem) if x.stem.isdigit() else 0)
            return [f.read_text(encoding="utf-8") for f in files]
        else:
            # Generate some default prompts
            default_prompt = "Explain the concept of neural networks and how they are used in modern AI applications."
            return [default_prompt] * 3

def main():
    if len(sys.argv) < 3:
        print("Usage: python cinematic_benchmark.py <GPU_NAME> <MODEL_NAME>")
        print("Example: python cinematic_benchmark.py RTX4090-48GB llama3.1:70b")
        sys.exit(1)
        
    gpu_name = sys.argv[1]
    model_name = sys.argv[2]
    
    benchmark = CinematicBenchmark(gpu_name, model_name)
    
    try:
        curses.wrapper(benchmark.run)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nBenchmark session completed!")
        print(f"Tested {model_name} on {gpu_name}")

if __name__ == "__main__":
    main()