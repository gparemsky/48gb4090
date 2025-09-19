#!/usr/bin/env python3
"""
Diagnostic GPU Benchmark Display - Monochrome Version
Clean, professional output optimized for screenshots and debugging
"""

import os
import sys
import time
import threading
import queue
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path
import openai
import curses
from collections import deque
import textwrap

# Configuration
base_url = "http://localhost:11434/v1/"
api_key = "ollama"
temperature = 0.7
top_p = 0.8
max_tokens = 2000
seed = 1000

# Display configuration
REFRESH_RATE = 20  # FPS for smooth output
FRAME_TIME = 1.0 / REFRESH_RATE

class GPUMonitor:
    """Enhanced GPU monitoring with detailed metrics"""
    
    def __init__(self):
        self.metrics = {
            'name': 'Unknown GPU',
            'temperature': 0,
            'fan_speed': 0,
            'power_draw': 0,
            'power_limit': 0,
            'memory_used': 0,
            'memory_total': 0,
            'memory_reserved': 0,
            'gpu_utilization': 0,
            'memory_utilization': 0,
            'clock_graphics': 0,
            'clock_memory': 0,
            'clock_sm': 0,
            'pcie_throughput_rx': 0,
            'pcie_throughput_tx': 0,
            'compute_mode': 'Default',
            'driver_version': 'Unknown',
            'cuda_version': 'Unknown'
        }
        self.metrics_lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.last_update = 0
        
    def start(self):
        self.thread.start()
        
    def stop(self):
        self.running = False
        
    def get_metrics(self):
        with self.metrics_lock:
            return self.metrics.copy()
            
    def _monitor_loop(self):
        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_update < 0.25:  # Update 4 times per second
                    time.sleep(0.05)
                    continue
                    
                # Query comprehensive GPU metrics
                result = subprocess.run([
                    'nvidia-smi',
                    '--query-gpu=name,temperature.gpu,fan.speed,power.draw,power.limit,memory.used,memory.total,memory.reserved,utilization.gpu,utilization.memory,clocks.current.graphics,clocks.current.memory,clocks.current.sm,pcie.link.width.current,compute_mode,driver_version',
                    '--format=csv,noheader,nounits'
                ], capture_output=True, text=True, timeout=1)
                
                if result.returncode == 0:
                    parts = result.stdout.strip().split(', ')
                    if len(parts) >= 15:
                        with self.metrics_lock:
                            self.metrics['name'] = parts[0]
                            self.metrics['temperature'] = int(float(parts[1]))
                            self.metrics['fan_speed'] = int(float(parts[2])) if parts[2] != '[N/A]' else 0
                            self.metrics['power_draw'] = float(parts[3]) if parts[3] != '[N/A]' else 0
                            self.metrics['power_limit'] = float(parts[4]) if parts[4] != '[N/A]' else 0
                            self.metrics['memory_used'] = int(float(parts[5]))
                            self.metrics['memory_total'] = int(float(parts[6]))
                            self.metrics['memory_reserved'] = int(float(parts[7])) if parts[7] != '[N/A]' else 0
                            self.metrics['gpu_utilization'] = int(float(parts[8]))
                            self.metrics['memory_utilization'] = int(float(parts[9])) if parts[9] != '[N/A]' else 0
                            self.metrics['clock_graphics'] = int(float(parts[10]))
                            self.metrics['clock_memory'] = int(float(parts[11]))
                            self.metrics['clock_sm'] = int(float(parts[12]))
                            self.metrics['pcie_width'] = parts[13] if parts[13] != '[N/A]' else 'x16'
                            self.metrics['compute_mode'] = parts[14]
                            self.metrics['driver_version'] = parts[15] if len(parts) > 15 else 'Unknown'
                            
                        # Calculate memory bandwidth (approximate)
                        # Memory bandwidth = memory_clock * bus_width * 2 (DDR) / 8 (bits to bytes)
                        # For 4090: 384-bit bus, for most others: 256-bit or 320-bit
                        bus_width = 384 if '4090' in self.metrics['name'] else 256
                        self.metrics['memory_bandwidth'] = (self.metrics['clock_memory'] * bus_width * 2) / 8 / 1000  # GB/s
                        
                        self.last_update = current_time
            except Exception:
                pass
            time.sleep(0.05)

class StreamingLLMHandler:
    """Handles LLM streaming with detailed metrics"""
    
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name
        self.response_queue = queue.Queue()
        self.metrics_queue = queue.Queue()
        self.word_queue = queue.Queue()
        self.is_streaming = False
        self.thread = None
        
    def start_streaming(self, messages):
        self.is_streaming = True
        self.response_queue.queue.clear()
        self.metrics_queue.queue.clear()
        self.word_queue.queue.clear()
        self.thread = threading.Thread(target=self._stream_worker, args=(messages,), daemon=True)
        self.thread.start()
        
    def _stream_worker(self, messages):
        start_time = time.time()
        first_token_time = None
        last_word_time = start_time
        prompt_tokens = len(messages[-1]["content"].split())
        response_text = ""
        current_word = ""
        total_tokens = 0
        
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
                if not self.is_streaming:
                    break
                    
                current_time = time.time()
                
                if first_token_time is None:
                    first_token_time = current_time
                    ttft = first_token_time - start_time
                    self.metrics_queue.put({
                        'ttft': ttft,
                        'time_to_first_token': ttft
                    })
                    
                # Extract token
                if hasattr(event, 'choices') and event.choices:
                    if hasattr(event.choices[0], 'delta') and hasattr(event.choices[0].delta, 'content'):
                        chunk = event.choices[0].delta.content
                        if chunk:
                            response_text += chunk
                            current_word += chunk
                            
                            # Check for word boundaries
                            if ' ' in chunk or '\n' in chunk:
                                words = current_word.split()
                                for word in words[:-1]:
                                    self.word_queue.put(word + ' ')
                                current_word = words[-1] if words else ""
                                
                            # Calculate detailed metrics
                            elapsed = current_time - start_time
                            generation_time = current_time - first_token_time if first_token_time else 0
                            
                            # Token counting (approximate)
                            total_tokens = len(response_text.split())
                            
                            if generation_time > 0:
                                tokens_per_sec = total_tokens / generation_time
                                chars_per_sec = len(response_text) / generation_time
                                
                                # Calculate inter-token latency
                                itl = generation_time / total_tokens if total_tokens > 0 else 0
                                
                                self.metrics_queue.put({
                                    'prompt_tokens': prompt_tokens,
                                    'completion_tokens': total_tokens,
                                    'total_tokens': prompt_tokens + total_tokens,
                                    'tokens_per_sec': tokens_per_sec,
                                    'chars_per_sec': chars_per_sec,
                                    'prompt_eval_rate': prompt_tokens / ttft if ttft > 0 else 0,
                                    'eval_rate': tokens_per_sec,
                                    'total_duration': elapsed,
                                    'generation_duration': generation_time,
                                    'inter_token_latency': itl * 1000,  # Convert to ms
                                    'response_length': len(response_text)
                                })
                                
            # Push remaining word
            if current_word:
                self.word_queue.put(current_word)
                
            # Final metrics
            if hasattr(event, 'usage'):
                final_metrics = {
                    'prompt_tokens_final': event.usage.prompt_tokens if hasattr(event.usage, 'prompt_tokens') else prompt_tokens,
                    'completion_tokens_final': event.usage.completion_tokens if hasattr(event.usage, 'completion_tokens') else total_tokens,
                    'total_tokens_final': event.usage.total_tokens if hasattr(event.usage, 'total_tokens') else prompt_tokens + total_tokens
                }
                self.metrics_queue.put(final_metrics)
                
        except Exception as e:
            self.word_queue.put(f"[ERROR: {str(e)}]")
        finally:
            self.is_streaming = False
            
    def get_word(self):
        try:
            return self.word_queue.get_nowait()
        except queue.Empty:
            return None
            
    def get_metrics_update(self):
        try:
            return self.metrics_queue.get_nowait()
        except queue.Empty:
            return None
            
    def stop_streaming(self):
        self.is_streaming = False

class DiagnosticBenchmark:
    """Monochrome diagnostic display for debugging and screenshots"""
    
    def __init__(self, gpu_name, model_name):
        self.gpu_name = gpu_name
        self.model_name = model_name
        self.gpu_monitor = GPUMonitor()
        self.client = openai.Client(base_url=base_url, api_key=api_key)
        self.llm_handler = StreamingLLMHandler(self.client, model_name)
        
        # Display state
        self.current_prompt = ""
        self.next_prompt = ""
        self.current_response = ""
        self.response_words = []
        
        # Detailed metrics
        self.metrics = {
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'tokens_per_sec': 0.0,
            'chars_per_sec': 0.0,
            'prompt_eval_rate': 0.0,
            'eval_rate': 0.0,
            'ttft': 0.0,
            'total_duration': 0.0,
            'generation_duration': 0.0,
            'inter_token_latency': 0.0,
            'response_length': 0
        }
        
        # History for mini-graphs
        self.gpu_util_history = deque(maxlen=40)
        self.temp_history = deque(maxlen=40)
        self.tps_history = deque(maxlen=40)
        
        self.stdscr = None
        self.running = True
        self.last_update = 0
        
    def draw_border(self, y, x, h, w, title=""):
        """Draw a simple monochrome border"""
        max_y, max_x = self.stdscr.getmaxyx()
        
        # Check bounds
        if y >= max_y or x >= max_x or y + h > max_y or x + w > max_x:
            return
            
        try:
            # Corners
            if y < max_y and x < max_x:
                self.stdscr.addstr(y, x, "+")
            if y < max_y and x + w - 1 < max_x:
                self.stdscr.addstr(y, x + w - 1, "+")
            if y + h - 1 < max_y and x < max_x:
                self.stdscr.addstr(y + h - 1, x, "+")
            if y + h - 1 < max_y and x + w - 1 < max_x:
                self.stdscr.addstr(y + h - 1, x + w - 1, "+")
            
            # Horizontal lines
            for i in range(x + 1, min(x + w - 1, max_x)):
                if y < max_y:
                    self.stdscr.addstr(y, i, "-")
                if y + h - 1 < max_y:
                    self.stdscr.addstr(y + h - 1, i, "-")
                
            # Vertical lines
            for i in range(y + 1, min(y + h - 1, max_y)):
                if x < max_x:
                    self.stdscr.addstr(i, x, "|")
                if x + w - 1 < max_x:
                    self.stdscr.addstr(i, x + w - 1, "|")
                
            # Title
            if title:
                title_str = f"[ {title} ]"
                title_x = x + (w - len(title_str)) // 2
                if y < max_y and title_x > 0 and title_x + len(title_str) < max_x:
                    self.stdscr.addstr(y, title_x, title_str[:max_x - title_x], curses.A_BOLD)
        except curses.error:
            pass
            
    def draw_mini_graph(self, y, x, width, data, label="", max_val=None):
        """Draw a mini ASCII graph"""
        if not data or len(data) < 2:
            return
            
        try:
            # Determine scale
            if max_val is None:
                max_val = max(data) if data else 1
            min_val = min(data) if data else 0
            range_val = max_val - min_val if max_val != min_val else 1
            
            # Sample data if too long
            if len(data) > width:
                step = len(data) / width
                sampled = [data[int(i * step)] for i in range(width)]
            else:
                sampled = list(data)
                
            # Draw graph using simple ASCII
            chars = " ._-^"
            graph_str = ""
            for val in sampled:
                normalized = (val - min_val) / range_val
                char_idx = min(len(chars) - 1, int(normalized * (len(chars) - 1)))
                graph_str += chars[char_idx]
                
            self.stdscr.addstr(y, x, graph_str[:width])
            
            # Add label with current value
            if label and x + width + 2 < curses.COLS:
                label_str = f" {label}: {data[-1]:.1f}" if data else f" {label}: --"
                self.stdscr.addstr(y, x + width, label_str)
        except curses.error:
            pass
            
    def format_bytes(self, bytes_val):
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f}{unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f}PB"
        
    def draw_dashboard(self):
        """Draw the diagnostic dashboard"""
        try:
            self.stdscr.clear()
        except:
            return
            
        height, width = self.stdscr.getmaxyx()
        
        # Minimum size check
        if height < 30 or width < 80:
            try:
                self.stdscr.addstr(0, 0, "Terminal too small! Need at least 80x30")
                self.stdscr.refresh()
            except:
                pass
            return
        
        # Title
        title = f"DIAGNOSTIC BENCHMARK - {self.model_name} on {self.gpu_name}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            self.stdscr.addstr(0, 1, title[:width-2], curses.A_BOLD)
            if width > len(timestamp) + 2:
                self.stdscr.addstr(0, max(1, width - len(timestamp) - 1), timestamp)
        except curses.error:
            pass
        
        # GPU METRICS SECTION (Top Left)
        gpu_y, gpu_x = 2, 1
        gpu_h, gpu_w = min(16, height - 4), min(48, width // 2)
        self.draw_border(gpu_y, gpu_x, gpu_h, gpu_w, "GPU METRICS")
        
        gpu = self.gpu_monitor.get_metrics()
        y = gpu_y + 1
        
        # Safe string output helper
        def safe_addstr(y, x, text, attr=0):
            try:
                if y < height and x < width:
                    self.stdscr.addstr(y, x, text[:width - x], attr)
            except curses.error:
                pass
        
        # GPU identification
        safe_addstr(y, gpu_x + 2, f"Device: {gpu['name'][:40]}")
        y += 1
        safe_addstr(y, gpu_x + 2, f"Driver: {gpu['driver_version']}")
        y += 2
        
        # Temperature and cooling
        temp_str = f"Temp: {gpu['temperature']}C"
        fan_str = f"Fan: {gpu['fan_speed']}%"
        safe_addstr(y, gpu_x + 2, temp_str)
        safe_addstr(y, gpu_x + 20, fan_str)
        y += 1
        
        # Power
        power_str = f"Power: {gpu['power_draw']:.1f}W / {gpu['power_limit']:.1f}W"
        efficiency = (gpu['power_draw'] / gpu['power_limit'] * 100) if gpu['power_limit'] > 0 else 0
        safe_addstr(y, gpu_x + 2, power_str)
        safe_addstr(y, gpu_x + 35, f"({efficiency:.0f}%)")
        y += 2
        
        # Clocks
        safe_addstr(y, gpu_x + 2, "CLOCKS:")
        y += 1
        safe_addstr(y, gpu_x + 2, f"  Core: {gpu['clock_graphics']}MHz")
        safe_addstr(y, gpu_x + 25, f"SM: {gpu['clock_sm']}MHz")
        y += 1
        safe_addstr(y, gpu_x + 2, f"  Mem:  {gpu['clock_memory']}MHz")
        safe_addstr(y, gpu_x + 25, f"BW: ~{gpu.get('memory_bandwidth', 0):.0f}GB/s")
        y += 2
        
        # Memory
        safe_addstr(y, gpu_x + 2, "MEMORY:")
        y += 1
        mem_used_gb = gpu['memory_used'] / 1024
        mem_total_gb = gpu['memory_total'] / 1024
        mem_percent = (gpu['memory_used'] / gpu['memory_total'] * 100) if gpu['memory_total'] > 0 else 0
        safe_addstr(y, gpu_x + 2, f"  Used: {mem_used_gb:.2f}GB / {mem_total_gb:.2f}GB ({mem_percent:.1f}%)")
        y += 1
        if gpu['memory_reserved'] > 0:
            safe_addstr(y, gpu_x + 2, f"  Reserved: {gpu['memory_reserved']}MB")
            y += 1
            
        # Utilization
        safe_addstr(y, gpu_x + 2, f"GPU Load: {gpu['gpu_utilization']}%")
        safe_addstr(y, gpu_x + 20, f"Mem Load: {gpu['memory_utilization']}%")
        
        # LLM METRICS SECTION (Top Right)
        llm_y, llm_x = 2, min(51, gpu_x + gpu_w + 2)
        llm_h, llm_w = min(16, height - 4), min(48, width - llm_x - 1)
        if llm_x + llm_w <= width:
            self.draw_border(llm_y, llm_x, llm_h, llm_w, "LLM METRICS")
            
            y = llm_y + 1
            safe_addstr(y, llm_x + 2, f"Model: {self.model_name[:40]}")
            y += 2
            
            # Token metrics
            safe_addstr(y, llm_x + 2, "TOKENS:", curses.A_BOLD)
            y += 1
            safe_addstr(y, llm_x + 2, f"  Prompt:     {self.metrics['prompt_tokens']:,}")
            y += 1
            safe_addstr(y, llm_x + 2, f"  Generated:  {self.metrics['completion_tokens']:,}")
            y += 1
            safe_addstr(y, llm_x + 2, f"  Total:      {self.metrics['total_tokens']:,}")
            y += 2
            
            # Performance metrics
            safe_addstr(y, llm_x + 2, "PERFORMANCE:", curses.A_BOLD)
            y += 1
            safe_addstr(y, llm_x + 2, f"  TTFT:       {self.metrics['ttft']:.3f}s")
            y += 1
            safe_addstr(y, llm_x + 2, f"  Tokens/sec: {self.metrics['tokens_per_sec']:.2f}")
            y += 1
            safe_addstr(y, llm_x + 2, f"  Prompt/sec: {self.metrics['prompt_eval_rate']:.2f}")
            y += 1
            safe_addstr(y, llm_x + 2, f"  ITL:        {self.metrics['inter_token_latency']:.1f}ms")
            y += 1
            safe_addstr(y, llm_x + 2, f"  Chars/sec:  {self.metrics['chars_per_sec']:.1f}")
        
        # PROMPT SECTION (Middle Left)
        prompt_y = min(19, gpu_y + gpu_h + 1)
        prompt_h = min(12, height - prompt_y - 5)
        prompt_w = min(48, width // 2)
        if prompt_y < height - 5:
            self.draw_border(prompt_y, 1, prompt_h, prompt_w, "PROMPTS")
            
            y = prompt_y + 1
            safe_addstr(y, 3, "CURRENT:", curses.A_BOLD)
            y += 1
            
            # Wrap and display current prompt
            if self.current_prompt:
                wrapped = textwrap.wrap(self.current_prompt, width=prompt_w - 4)
                for i, line in enumerate(wrapped[:4]):
                    if y < prompt_y + prompt_h - 5:
                        safe_addstr(y, 3, line[:prompt_w - 4])
                        y += 1
                if len(wrapped) > 4:
                    safe_addstr(y, 3, "...")
                    y += 1
            else:
                safe_addstr(y, 3, "[No prompt loaded]")
                y += 1
                
            y = prompt_y + prompt_h - 5
            safe_addstr(y, 3, "NEXT:", curses.A_BOLD)
            y += 1
            
            # Show next prompt preview
            if self.next_prompt:
                wrapped = textwrap.wrap(self.next_prompt, width=prompt_w - 4)
                for i, line in enumerate(wrapped[:2]):
                    if y < prompt_y + prompt_h - 1:
                        safe_addstr(y, 3, line[:prompt_w - 4], curses.A_DIM)
                        y += 1
                if len(wrapped) > 2:
                    safe_addstr(y, 3, "...", curses.A_DIM)
            else:
                safe_addstr(y, 3, "[End of queue]", curses.A_DIM)
            
        # OUTPUT SECTION (Middle Right)
        output_y = prompt_y
        output_x = min(51, prompt_w + 3)
        output_h = prompt_h
        output_w = min(48, width - output_x - 1)
        if output_x + output_w <= width and prompt_y < height - 5:
            self.draw_border(output_y, output_x, output_h, output_w, "OUTPUT")
            
            y = output_y + 1
            safe_addstr(y, output_x + 2, "RESPONSE:", curses.A_BOLD)
            y += 1
            
            # Display response with word-by-word update
            if self.current_response:
                # Wrap response text
                wrapped = textwrap.wrap(self.current_response, width=output_w - 4)
                display_lines = min(len(wrapped), output_h - 4)
                
                # Show last N lines to keep most recent output visible
                start_line = max(0, len(wrapped) - display_lines)
                for i, line in enumerate(wrapped[start_line:start_line + display_lines]):
                    if y < output_y + output_h - 2:
                        safe_addstr(y, output_x + 2, line[:output_w - 4])
                        y += 1
                        
                # Show cursor/typing indicator
                if self.llm_handler.is_streaming:
                    if y < output_y + output_h - 1:
                        safe_addstr(y, output_x + 2, "█", curses.A_BLINK)
            else:
                safe_addstr(y, output_x + 2, "[Waiting for response...]", curses.A_DIM)
                
            # Response stats
            y = output_y + output_h - 2
            stats_str = f"Words: {len(self.current_response.split())}  Chars: {len(self.current_response)}"
            safe_addstr(y, output_x + 2, stats_str, curses.A_DIM)
        
        # GRAPHS SECTION (Bottom)
        graph_y = 32
        if graph_y + 4 < height:
            self.draw_border(graph_y, 1, 4, width - 2, "PERFORMANCE GRAPHS")
            
            # Update history
            self.gpu_util_history.append(gpu['gpu_utilization'])
            self.temp_history.append(gpu['temperature'])
            if self.metrics['tokens_per_sec'] > 0:
                self.tps_history.append(self.metrics['tokens_per_sec'])
                
            # Draw mini graphs
            y = graph_y + 1
            self.draw_mini_graph(y, 3, 30, self.gpu_util_history, "GPU%", 100)
            y += 1
            self.draw_mini_graph(y, 3, 30, self.temp_history, "Temp", 100)
            
            if len(self.tps_history) > 1:
                self.draw_mini_graph(y - 1, 40, 30, self.tps_history, "Tok/s")
                
        # Status bar
        if height > 1:
            status_y = height - 1
            status = f" [q]uit | [s]kip | Frame: {int(1000/FRAME_TIME/1000)}fps | {self.model_name} "
            try:
                self.stdscr.addstr(status_y, 0, " " * min(width, curses.COLS), curses.A_REVERSE)
                self.stdscr.addstr(status_y, 0, status[:min(width, curses.COLS)], curses.A_REVERSE)
            except curses.error:
                pass
        
        try:
            self.stdscr.refresh()
        except curses.error:
            pass
        
    def run_prompt_test(self, prompt_text, next_prompt_text=""):
        """Run a single prompt test"""
        self.current_prompt = prompt_text
        self.next_prompt = next_prompt_text
        self.current_response = ""
        self.response_words = []
        
        # Reset metrics
        self.metrics = {k: 0 for k in self.metrics}
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt_text}
        ]
        
        # Start streaming
        self.llm_handler.start_streaming(messages)
        
        # Update display while streaming
        last_update = time.time()
        while self.llm_handler.is_streaming or self.llm_handler.word_queue.qsize() > 0:
            current_time = time.time()
            
            # Get new words
            word = self.llm_handler.get_word()
            while word:
                self.response_words.append(word)
                self.current_response = "".join(self.response_words)
                word = self.llm_handler.get_word()
                
            # Get metrics updates
            metrics = self.llm_handler.get_metrics_update()
            if metrics:
                self.metrics.update(metrics)
                
            # Update display at target framerate
            if current_time - last_update >= FRAME_TIME:
                self.draw_dashboard()
                last_update = current_time
                
            # Check for user input
            try:
                key = self.stdscr.getch()
                if key == ord('q'):
                    self.running = False
                    self.llm_handler.stop_streaming()
                    break
                elif key == ord('s'):
                    self.llm_handler.stop_streaming()
                    break
            except:
                pass
                
            time.sleep(0.01)  # Small sleep to prevent CPU spinning
            
        # Final update
        self.draw_dashboard()
        
    def run(self, stdscr):
        """Main run loop"""
        self.stdscr = stdscr
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)    # Non-blocking input
        
        # No colors - pure monochrome
        curses.use_default_colors()
        
        self.gpu_monitor.start()
        
        # Load prompts
        prompts = self.load_prompts()
        
        try:
            # Initial display
            for _ in range(10):
                self.draw_dashboard()
                time.sleep(0.1)
                
            prompt_index = 0
            while self.running and prompt_index < len(prompts):
                # Determine next prompt
                next_prompt = prompts[prompt_index + 1] if prompt_index + 1 < len(prompts) else ""
                
                # Run test
                self.run_prompt_test(prompts[prompt_index], next_prompt)
                
                if not self.running:
                    break
                    
                # Cool down with countdown
                if prompt_index < len(prompts) - 1:
                    cooldown = 10
                    start_time = time.time()
                    
                    while time.time() - start_time < cooldown:
                        remaining = cooldown - int(time.time() - start_time)
                        
                        # Update display
                        self.draw_dashboard()
                        
                        # Show cooldown
                        try:
                            y = curses.LINES - 1
                            cooldown_text = f" Cooldown: {remaining}s | Next: Prompt {prompt_index + 2}/{len(prompts)} "
                            self.stdscr.addstr(y, curses.COLS - len(cooldown_text) - 1, 
                                             cooldown_text, curses.A_REVERSE)
                            self.stdscr.refresh()
                        except:
                            pass
                            
                        # Check for input
                        try:
                            key = stdscr.getch()
                            if key == ord('q'):
                                self.running = False
                                break
                            elif key == ord('s'):
                                break
                        except:
                            pass
                            
                        time.sleep(FRAME_TIME)
                        
                    if not self.running:
                        break
                        
                prompt_index += 1
                
        finally:
            self.gpu_monitor.stop()
            
    def load_prompts(self):
        """Load test prompts"""
        prompts_dir = Path("prompts")
        if prompts_dir.exists():
            files = sorted(prompts_dir.glob("*.txt"), 
                         key=lambda x: int(x.stem) if x.stem.isdigit() else 0)
            return [f.read_text(encoding="utf-8") for f in files]
        else:
            default = "Explain quantum computing in simple terms."
            return [default] * 3

def main():
    if len(sys.argv) < 3:
        print("Usage: python diagnostic_benchmark.py <GPU_NAME> <MODEL_NAME>")
        print("Example: python diagnostic_benchmark.py RTX4090-48GB llama3.1:70b")
        sys.exit(1)
        
    gpu_name = sys.argv[1]
    model_name = sys.argv[2]
    
    benchmark = DiagnosticBenchmark(gpu_name, model_name)
    
    try:
        curses.wrapper(benchmark.run)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nDiagnostic benchmark completed!")
        print(f"Tested {model_name} on {gpu_name}")

if __name__ == "__main__":
    main()