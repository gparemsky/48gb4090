#!/usr/bin/env python3
"""
Cinematic GPU Benchmark Dashboard - Smooth Version
Real-time visual display with reduced flickering and better performance
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
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Configuration
base_url = "http://localhost:11434/v1/"
api_key = "ollama"
temperature = 0.7
top_p = 0.8
max_tokens = 2000
seed = 1000

# Display configuration
REFRESH_RATE = 30  # FPS target
FRAME_TIME = 1.0 / REFRESH_RATE

class GPUMonitor:
    """Monitors GPU metrics in real-time with caching"""
    
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
        self.metrics_lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.last_update = 0
        
    def start(self):
        self.thread.start()
        
    def stop(self):
        self.running = False
        
    def get_metrics(self):
        """Get metrics with thread safety"""
        with self.metrics_lock:
            return self.metrics.copy()
            
    def _monitor_loop(self):
        """Monitor loop with controlled update rate"""
        while self.running:
            try:
                # Only update every 500ms to reduce overhead
                current_time = time.time()
                if current_time - self.last_update < 0.5:
                    time.sleep(0.1)
                    continue
                    
                result = subprocess.run([
                    'nvidia-smi',
                    '--query-gpu=name,temperature.gpu,fan.speed,power.draw,memory.used,memory.total,utilization.gpu,clocks.current.graphics',
                    '--format=csv,noheader,nounits'
                ], capture_output=True, text=True, timeout=1)
                
                if result.returncode == 0:
                    parts = result.stdout.strip().split(', ')
                    if len(parts) >= 8:
                        with self.metrics_lock:
                            self.metrics['name'] = parts[0]
                            self.metrics['temperature'] = int(float(parts[1]))
                            self.metrics['fan_speed'] = int(float(parts[2])) if parts[2] != '[N/A]' else 0
                            self.metrics['power_draw'] = int(float(parts[3])) if parts[3] != '[N/A]' else 0
                            self.metrics['memory_used'] = int(float(parts[4]))
                            self.metrics['memory_total'] = int(float(parts[5]))
                            self.metrics['gpu_utilization'] = int(float(parts[6]))
                            self.metrics['clock_speed'] = int(float(parts[7]))
                        self.last_update = current_time
            except Exception:
                pass
            time.sleep(0.1)

class StreamingLLMHandler:
    """Handles LLM streaming in a separate thread"""
    
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name
        self.response_queue = queue.Queue()
        self.metrics_queue = queue.Queue()
        self.is_streaming = False
        self.executor = ThreadPoolExecutor(max_workers=1)
        
    def start_streaming(self, messages):
        """Start streaming in background thread"""
        self.is_streaming = True
        self.response_queue.queue.clear()
        self.metrics_queue.queue.clear()
        future = self.executor.submit(self._stream_worker, messages)
        return future
        
    def _stream_worker(self, messages):
        """Worker thread for streaming"""
        start_time = time.time()
        first_token_time = None
        prompt_tokens = len(messages[-1]["content"].split())
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
                if not self.is_streaming:
                    break
                    
                if first_token_time is None:
                    first_token_time = time.time()
                    ttft = first_token_time - start_time
                    self.metrics_queue.put({'ttft': ttft})
                    
                # Extract token if available
                if hasattr(event, 'choices') and event.choices:
                    if hasattr(event.choices[0], 'delta') and hasattr(event.choices[0].delta, 'content'):
                        chunk = event.choices[0].delta.content
                        if chunk:
                            response_chunks.append(chunk)
                            self.response_queue.put(chunk)
                            
                            # Update metrics periodically
                            elapsed = time.time() - start_time
                            if first_token_time and elapsed > ttft:
                                completion_tokens = len("".join(response_chunks).split())
                                tokens_per_sec = completion_tokens / (elapsed - ttft)
                                prompt_speed = prompt_tokens / ttft if ttft > 0 else 0
                                
                                self.metrics_queue.put({
                                    'completion_tokens': completion_tokens,
                                    'tokens_per_sec': tokens_per_sec,
                                    'prompt_speed': prompt_speed,
                                    'prompt_tokens': prompt_tokens
                                })
                                
            # Final metrics
            if hasattr(event, 'usage'):
                final_metrics = {
                    'prompt_tokens': event.usage.prompt_tokens if hasattr(event.usage, 'prompt_tokens') else prompt_tokens,
                    'completion_tokens': event.usage.completion_tokens if hasattr(event.usage, 'completion_tokens') else len("".join(response_chunks).split())
                }
                self.metrics_queue.put(final_metrics)
                
        except Exception as e:
            self.response_queue.put(f"Error: {str(e)}")
        finally:
            self.is_streaming = False
            
    def get_response_chunk(self):
        """Get response chunk without blocking"""
        try:
            return self.response_queue.get_nowait()
        except queue.Empty:
            return None
            
    def get_metrics_update(self):
        """Get metrics update without blocking"""
        try:
            return self.metrics_queue.get_nowait()
        except queue.Empty:
            return None
            
    def stop_streaming(self):
        """Stop current streaming"""
        self.is_streaming = False

class SmoothDisplay:
    """Manages smooth display updates with double buffering"""
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.buffer = curses.newpad(self.height + 100, self.width + 100)
        self.last_frame_time = 0
        
    def should_update(self):
        """Check if enough time has passed for next frame"""
        current_time = time.time()
        if current_time - self.last_frame_time >= FRAME_TIME:
            self.last_frame_time = current_time
            return True
        return False
        
    def clear_buffer(self):
        """Clear the buffer"""
        self.buffer.clear()
        
    def refresh(self):
        """Refresh display from buffer"""
        try:
            self.buffer.refresh(0, 0, 0, 0, self.height - 1, self.width - 1)
        except curses.error:
            pass  # Ignore refresh errors

class CinematicBenchmark:
    """Main cinematic benchmark display with smooth updates"""
    
    def __init__(self, gpu_name, model_name):
        self.gpu_name = gpu_name
        self.model_name = model_name
        self.gpu_monitor = GPUMonitor()
        self.client = openai.Client(base_url=base_url, api_key=api_key)
        self.llm_handler = StreamingLLMHandler(self.client, model_name)
        
        # Performance metrics
        self.current_prompt = ""
        self.current_response = ""
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.ttft = 0.0
        self.tokens_per_sec = 0.0
        self.prompt_speed = 0.0
        
        # History for graphs (with smoothing)
        self.temp_history = deque(maxlen=60)
        self.util_history = deque(maxlen=60)
        self.tps_history = deque(maxlen=30)
        
        # Smooth value tracking
        self.smooth_temp = 0
        self.smooth_util = 0
        self.smooth_tps = 0
        
        # Colors
        self.colors = {}
        self.display = None
        self.running = True
        
    def init_colors(self):
        """Initialize color pairs for the display"""
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        curses.init_pair(3, curses.COLOR_RED, -1)
        curses.init_pair(4, curses.COLOR_CYAN, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_WHITE, -1)
        curses.init_pair(7, curses.COLOR_BLUE, -1)
        
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
        """Draw a box on the buffer"""
        if color is None:
            color = self.colors['frame']
        
        buffer = self.display.buffer
        
        try:
            # Draw corners
            buffer.addstr(y, x, "╔", color)
            buffer.addstr(y, x + w - 1, "╗", color)
            buffer.addstr(y + h - 1, x, "╚", color)
            buffer.addstr(y + h - 1, x + w - 1, "╝", color)
            
            # Draw horizontal lines
            for i in range(x + 1, x + w - 1):
                buffer.addstr(y, i, "═", color)
                buffer.addstr(y + h - 1, i, "═", color)
                
            # Draw vertical lines
            for i in range(y + 1, y + h - 1):
                buffer.addstr(i, x, "║", color)
                buffer.addstr(i, x + w - 1, "║", color)
                
            # Add title if provided
            if title:
                title_str = f" {title} "
                title_x = x + (w - len(title_str)) // 2
                buffer.addstr(y, title_x, title_str, color | curses.A_BOLD)
        except curses.error:
            pass
            
    def draw_progress_bar(self, y, x, width, value, max_val, label="", color=None):
        """Draw a smooth progress bar"""
        if color is None:
            color = self.colors['success']
            
        buffer = self.display.buffer
        
        if max_val == 0:
            percentage = 0
        else:
            percentage = min(100, int((value / max_val) * 100))
            
        filled = int((width - 2) * (percentage / 100))
        
        try:
            # Draw the bar
            buffer.addstr(y, x, "[", self.colors['frame'])
            for i in range(width - 2):
                if i < filled:
                    buffer.addstr(y, x + 1 + i, "█", color)
                else:
                    buffer.addstr(y, x + 1 + i, "░", curses.A_DIM)
            buffer.addstr(y, x + width - 1, "]", self.colors['frame'])
            
            # Add label
            if label:
                label_str = f" {label}: {percentage}%"
                if x + width + len(label_str) < self.display.width:
                    buffer.addstr(y, x + width + 1, label_str, self.colors['info'])
        except curses.error:
            pass
            
    def draw_sparkline(self, y, x, width, data, label=""):
        """Draw a smooth sparkline graph"""
        if not data or len(data) < 2:
            return
            
        buffer = self.display.buffer
        sparks = " ▁▂▃▄▅▆▇█"
        
        try:
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
                    buffer.addstr(y, x + i, sparks[spark_idx], color)
                    
            # Add label
            if label and x + width + 2 < self.display.width:
                buffer.addstr(y, x + width + 2, label, self.colors['info'])
        except curses.error:
            pass
            
    def smooth_value(self, current, target, factor=0.3):
        """Smooth value transitions"""
        return current + (target - current) * factor
        
    def format_response_preview(self, text, max_lines=8, max_width=70):
        """Format response text for preview window"""
        if not text:
            return ["Waiting for response..."]
            
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
        """Draw the main dashboard to buffer"""
        if not self.display or not self.display.should_update():
            return
            
        self.display.clear_buffer()
        buffer = self.display.buffer
        height, width = self.display.height, self.display.width
        
        try:
            # Title bar
            title = "╔════ GPU BENCHMARK CINEMATIC DASHBOARD ════╗"
            subtitle = f"Testing {self.model_name} on {self.gpu_name}"
            title_x = (width - len(title)) // 2
            subtitle_x = (width - len(subtitle)) // 2
            
            buffer.addstr(0, max(0, title_x), title[:width], self.colors['accent'] | curses.A_BOLD)
            buffer.addstr(1, max(0, subtitle_x), subtitle[:width], self.colors['info'])
            
            # GPU Metrics Panel
            gpu_box_y, gpu_box_x = 3, 2
            gpu_box_h, gpu_box_w = 12, min(45, width // 2 - 3)
            self.draw_box(gpu_box_y, gpu_box_x, gpu_box_h, gpu_box_w, "GPU METRICS", self.colors['success'])
            
            metrics = self.gpu_monitor.get_metrics()
            
            # Smooth values for display
            self.smooth_temp = self.smooth_value(self.smooth_temp, metrics['temperature'])
            self.smooth_util = self.smooth_value(self.smooth_util, metrics['gpu_utilization'])
            
            y_offset = gpu_box_y + 2
            
            # GPU Name
            buffer.addstr(y_offset, gpu_box_x + 2, f"GPU: {metrics['name'][:35]}", self.colors['bright'])
            y_offset += 2
            
            # Temperature with smooth transition
            temp_color = self.colors['success']
            if self.smooth_temp > 80:
                temp_color = self.colors['error']
            elif self.smooth_temp > 70:
                temp_color = self.colors['warning']
            buffer.addstr(y_offset, gpu_box_x + 2, f"Temp: {int(self.smooth_temp)}°C", temp_color)
            buffer.addstr(y_offset, gpu_box_x + 20, f"Fan: {metrics['fan_speed']}%", self.colors['info'])
            y_offset += 1
            
            # Power and Clock
            buffer.addstr(y_offset, gpu_box_x + 2, f"Power: {metrics['power_draw']}W", self.colors['info'])
            buffer.addstr(y_offset, gpu_box_x + 20, f"Clock: {metrics['clock_speed']}MHz", self.colors['info'])
            y_offset += 2
            
            # Memory usage bar
            self.draw_progress_bar(y_offset, gpu_box_x + 8, 30, metrics['memory_used'], metrics['memory_total'])
            y_offset += 1
            buffer.addstr(y_offset, gpu_box_x + 8, f"{metrics['memory_used']}MB / {metrics['memory_total']}MB", self.colors['info'])
            y_offset += 2
            
            # GPU Utilization bar with smooth transition
            util_color = self.colors['success']
            if self.smooth_util > 90:
                util_color = self.colors['error']
            elif self.smooth_util > 70:
                util_color = self.colors['warning']
            self.draw_progress_bar(y_offset, gpu_box_x + 8, 30, int(self.smooth_util), 100, color=util_color)
            
            # Performance Metrics Panel
            perf_box_x = gpu_box_x + gpu_box_w + 3
            if perf_box_x + 45 <= width:
                perf_box_w = min(45, width - perf_box_x - 2)
                self.draw_box(gpu_box_y, perf_box_x, gpu_box_h, perf_box_w, "PERFORMANCE", self.colors['accent'])
                
                y_offset = gpu_box_y + 2
                buffer.addstr(y_offset, perf_box_x + 2, "━━━ Token Statistics ━━━", self.colors['bright'])
                y_offset += 2
                
                buffer.addstr(y_offset, perf_box_x + 2, f"Prompt Tokens:  {self.prompt_tokens:,}", self.colors['info'])
                y_offset += 1
                buffer.addstr(y_offset, perf_box_x + 2, f"Output Tokens:  {self.completion_tokens:,}", self.colors['info'])
                y_offset += 2
                
                buffer.addstr(y_offset, perf_box_x + 2, "━━━ Speed Metrics ━━━", self.colors['bright'])
                y_offset += 2
                
                # Smooth tokens per second
                self.smooth_tps = self.smooth_value(self.smooth_tps, self.tokens_per_sec)
                tps_color = self.colors['success']
                if self.smooth_tps < 10:
                    tps_color = self.colors['error']
                elif self.smooth_tps < 30:
                    tps_color = self.colors['warning']
                    
                buffer.addstr(y_offset, perf_box_x + 2, f"TTFT: {self.ttft:.2f}s", self.colors['info'])
                y_offset += 1
                buffer.addstr(y_offset, perf_box_x + 2, f"Gen Speed: {self.smooth_tps:.1f} tok/s", tps_color)
                y_offset += 1
                buffer.addstr(y_offset, perf_box_x + 2, f"Prompt Speed: {self.prompt_speed:.1f} tok/s", self.colors['info'])
            
            # Prompt and Response panels
            text_panel_y = 16
            if text_panel_y + 10 < height:
                # Prompt Preview Panel
                prompt_box_w = min(45, width // 2 - 3)
                self.draw_box(text_panel_y, gpu_box_x, 10, prompt_box_w, "CURRENT PROMPT", self.colors['info'])
                
                prompt_lines = self.format_response_preview(self.current_prompt, max_lines=7, max_width=prompt_box_w - 4)
                for i, line in enumerate(prompt_lines[:7]):
                    if text_panel_y + 2 + i < text_panel_y + 9:
                        buffer.addstr(text_panel_y + 2 + i, gpu_box_x + 2, line[:prompt_box_w - 4], self.colors['bright'])
                
                # Response Preview Panel
                resp_box_x = gpu_box_x + prompt_box_w + 3
                if resp_box_x + 45 <= width:
                    resp_box_w = min(45, width - resp_box_x - 2)
                    self.draw_box(text_panel_y, resp_box_x, 10, resp_box_w, "MODEL RESPONSE", self.colors['success'])
                    
                    response_lines = self.format_response_preview(self.current_response, max_lines=7, max_width=resp_box_w - 4)
                    for i, line in enumerate(response_lines[:7]):
                        if text_panel_y + 2 + i < text_panel_y + 9:
                            color = self.colors['bright'] if i < len(response_lines) - 1 else self.colors['success']
                            buffer.addstr(text_panel_y + 2 + i, resp_box_x + 2, line[:resp_box_w - 4], color)
            
            # Graph Panel
            graph_box_y = 27
            if graph_box_y + 3 < height:
                graph_box_h = min(8, height - graph_box_y - 1)
                graph_box_w = width - 4
                self.draw_box(graph_box_y, 2, graph_box_h, graph_box_w, "LIVE METRICS", self.colors['frame'])
                
                # Update history with smoothed values
                self.temp_history.append(int(self.smooth_temp))
                self.util_history.append(int(self.smooth_util))
                if self.smooth_tps > 0:
                    self.tps_history.append(self.smooth_tps)
                
                # Draw sparklines
                if graph_box_h > 4 and len(self.temp_history) > 1:
                    self.draw_sparkline(graph_box_y + 2, 4, min(40, graph_box_w - 20), 
                                      self.temp_history, f"Temp: {int(self.smooth_temp)}°C")
                    
                    self.draw_sparkline(graph_box_y + 3, 4, min(40, graph_box_w - 20), 
                                      self.util_history, f"Load: {int(self.smooth_util)}%")
                    
                    if graph_box_h > 5 and len(self.tps_history) > 1:
                        self.draw_sparkline(graph_box_y + 4, 4, min(40, graph_box_w - 20), 
                                          self.tps_history, f"Speed: {self.smooth_tps:.1f} t/s")
            
            # Status bar
            status_y = height - 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            status_text = f" {timestamp} | Press 'q' to quit | Press 's' to skip prompt "
            buffer.addstr(status_y, 0, status_text[:width], self.colors['frame'] | curses.A_REVERSE)
            
        except curses.error:
            pass
            
        self.display.refresh()
        
    def run_prompt_test(self, prompt_text, prompt_num, total_prompts):
        """Run a single prompt test with non-blocking updates"""
        self.current_prompt = prompt_text
        self.current_response = ""
        self.prompt_tokens = len(prompt_text.split())
        self.completion_tokens = 0
        self.ttft = 0
        self.tokens_per_sec = 0
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt_text}
        ]
        
        # Start streaming in background
        future = self.llm_handler.start_streaming(messages)
        
        # Update display while streaming
        while self.llm_handler.is_streaming or not future.done():
            # Get response chunks without blocking
            chunk = self.llm_handler.get_response_chunk()
            if chunk:
                self.current_response += chunk
                
            # Get metrics updates without blocking
            metrics = self.llm_handler.get_metrics_update()
            if metrics:
                self.ttft = metrics.get('ttft', self.ttft)
                self.prompt_tokens = metrics.get('prompt_tokens', self.prompt_tokens)
                self.completion_tokens = metrics.get('completion_tokens', self.completion_tokens)
                self.tokens_per_sec = metrics.get('tokens_per_sec', self.tokens_per_sec)
                self.prompt_speed = metrics.get('prompt_speed', self.prompt_speed)
                
            # Update display
            self.draw_dashboard()
            
            # Check for user input
            try:
                key = self.display.stdscr.getch()
                if key == ord('q'):
                    self.running = False
                    self.llm_handler.stop_streaming()
                    break
                elif key == ord('s'):
                    self.llm_handler.stop_streaming()
                    break
            except:
                pass
                
            time.sleep(FRAME_TIME)
            
    def run(self, stdscr):
        """Main run loop with smooth updates"""
        self.display = SmoothDisplay(stdscr)
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)    # Non-blocking input
        
        self.init_colors()
        self.gpu_monitor.start()
        
        # Initialize smooth values
        initial_metrics = self.gpu_monitor.get_metrics()
        self.smooth_temp = initial_metrics['temperature']
        self.smooth_util = initial_metrics['gpu_utilization']
        self.smooth_tps = 0
        
        # Load prompts
        prompts = self.load_prompts()
        
        try:
            prompt_index = 0
            
            # Initial display update loop before starting tests
            for _ in range(30):  # Show dashboard for 1 second before starting
                self.draw_dashboard()
                time.sleep(FRAME_TIME)
                
            while self.running and prompt_index < len(prompts):
                # Run test for current prompt
                self.run_prompt_test(prompts[prompt_index], prompt_index + 1, len(prompts))
                
                if not self.running:
                    break
                    
                # Cool down period with smooth countdown
                if prompt_index < len(prompts) - 1:
                    cooldown_duration = 10
                    cooldown_start = time.time()
                    
                    while time.time() - cooldown_start < cooldown_duration:
                        remaining = cooldown_duration - int(time.time() - cooldown_start)
                        
                        # Update display during cooldown
                        self.draw_dashboard()
                        
                        # Show cooldown message
                        try:
                            cooldown_text = f" Cooling down: {remaining}s | Next prompt: {prompt_index + 2}/{len(prompts)} "
                            y = self.display.height - 1
                            x = (self.display.width - len(cooldown_text)) // 2
                            self.display.buffer.addstr(y, max(0, x), cooldown_text[:self.display.width], 
                                                      self.colors['warning'] | curses.A_REVERSE)
                            self.display.refresh()
                        except curses.error:
                            pass
                            
                        # Check for user input
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
            self.llm_handler.executor.shutdown(wait=False)
            
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
        print("Usage: python cinematic_benchmark_smooth.py <GPU_NAME> <MODEL_NAME>")
        print("Example: python cinematic_benchmark_smooth.py RTX4090-48GB llama3.1:70b")
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