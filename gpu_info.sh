#!/bin/bash

# Output file with timestamp
OUTPUT_FILE="gpu_info_$(hostname)_$(date +%Y%m%d_%H%M%S).txt"

echo "Collecting GPU information for $(hostname)..." | tee $OUTPUT_FILE
echo "==========================================" | tee -a $OUTPUT_FILE
echo "" | tee -a $OUTPUT_FILE

# Get GPU name dynamically
GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)

# Basic GPU identification
echo "=== GPU IDENTIFICATION ===" | tee -a $OUTPUT_FILE
nvidia-smi -L | tee -a $OUTPUT_FILE
echo "" | tee -a $OUTPUT_FILE

# Core GPU specifications (vertical format)
echo "=== GPU SPECIFICATIONS ===" | tee -a $OUTPUT_FILE
{
    echo "GPU Name: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
    echo "Driver Version: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader)"
    echo "Compute Capability: $(nvidia-smi --query-gpu=compute_cap --format=csv,noheader)"
    echo "Total Memory: $(nvidia-smi --query-gpu=memory.total --format=csv,noheader)"
    echo "Free Memory: $(nvidia-smi --query-gpu=memory.free --format=csv,noheader)"
    echo "Used Memory: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader)"
    echo "GPU Utilization: $(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader)"
    echo "Memory Utilization: $(nvidia-smi --query-gpu=utilization.memory --format=csv,noheader)"
    echo "Temperature: $(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits)°C"
    echo "Power Draw: $(nvidia-smi --query-gpu=power.draw --format=csv,noheader)"
    echo "Power Limit: $(nvidia-smi --query-gpu=power.limit --format=csv,noheader)"
    echo "Current Graphics Clock: $(nvidia-smi --query-gpu=clocks.current.graphics --format=csv,noheader)"
    echo "Current Memory Clock: $(nvidia-smi --query-gpu=clocks.current.memory --format=csv,noheader)"
    echo "Max Graphics Clock: $(nvidia-smi --query-gpu=clocks.max.graphics --format=csv,noheader)"
    echo "Max Memory Clock: $(nvidia-smi --query-gpu=clocks.max.memory --format=csv,noheader)"
} | tee -a $OUTPUT_FILE
echo "" | tee -a $OUTPUT_FILE

# Run deviceQuery if available - most important metrics
if [ -f "./deviceQuery" ]; then
    echo "=== COMPUTE CAPABILITIES ===" | tee -a $OUTPUT_FILE
    ./deviceQuery | grep -E "Device 0:|CUDA Driver Version|CUDA Capability|Total amount of global memory|Multiprocessors|CUDA Cores/MP|GPU Max Clock|Memory Clock rate|Memory Bus Width|L2 Cache Size" | sed 's/^  //' | tee -a $OUTPUT_FILE
    echo "" | tee -a $OUTPUT_FILE
    
    # Calculate bandwidth
    echo "=== MEMORY BANDWIDTH ===" | tee -a $OUTPUT_FILE
    mem_clock=$(./deviceQuery | grep "Memory Clock rate" | awk '{print $4}')
    bus_width=$(./deviceQuery | grep "Memory Bus Width" | awk '{print $4}' | sed 's/-bit//')
    
    if [ ! -z "$mem_clock" ] && [ ! -z "$bus_width" ]; then
        # Determine memory type based on bus width
        if [ "$bus_width" -ge "4096" ]; then
            mem_type="HBM2e"
            multiplier=2
        else
            mem_type="GDDR6"
            multiplier=2
        fi
        
        bandwidth=$(echo "scale=2; ($mem_clock * $bus_width * $multiplier) / 8 / 1000" | bc)
        echo "Memory Type: $mem_type (detected from bus width)" | tee -a $OUTPUT_FILE
        echo "Memory Clock: $mem_clock MHz" | tee -a $OUTPUT_FILE
        echo "Bus Width: $bus_width bits" | tee -a $OUTPUT_FILE
        echo "Calculated Peak Bandwidth: $bandwidth GB/s" | tee -a $OUTPUT_FILE
    fi
    echo "" | tee -a $OUTPUT_FILE
fi

# Current operating status
echo "=== CURRENT STATUS ===" | tee -a $OUTPUT_FILE
pstate=$(nvidia-smi --query-gpu=pstate --format=csv,noheader)
temp=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits)
power=$(nvidia-smi --query-gpu=power.draw --format=csv,noheader)
gr_clock=$(nvidia-smi --query-gpu=clocks.gr --format=csv,noheader)
mem_clock=$(nvidia-smi --query-gpu=clocks.mem --format=csv,noheader)
gpu_util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader)
mem_util=$(nvidia-smi --query-gpu=utilization.memory --format=csv,noheader)

echo "P-State: $pstate" | tee -a $OUTPUT_FILE
echo "Temperature: $temp°C" | tee -a $OUTPUT_FILE
echo "Power Draw: $power" | tee -a $OUTPUT_FILE
echo "Graphics Clock: $gr_clock" | tee -a $OUTPUT_FILE
echo "Memory Clock: $mem_clock" | tee -a $OUTPUT_FILE
echo "GPU Utilization: $gpu_util" | tee -a $OUTPUT_FILE
echo "Memory Utilization: $mem_util" | tee -a $OUTPUT_FILE
echo "" | tee -a $OUTPUT_FILE

# Power limits
echo "=== POWER LIMITS ===" | tee -a $OUTPUT_FILE
echo "Current Limit: $(nvidia-smi --query-gpu=power.limit --format=csv,noheader)" | tee -a $OUTPUT_FILE
echo "Default Limit: $(nvidia-smi --query-gpu=power.default_limit --format=csv,noheader)" | tee -a $OUTPUT_FILE
echo "Min Limit: $(nvidia-smi --query-gpu=power.min_limit --format=csv,noheader)" | tee -a $OUTPUT_FILE
echo "Max Limit: $(nvidia-smi --query-gpu=power.max_limit --format=csv,noheader)" | tee -a $OUTPUT_FILE
echo "" | tee -a $OUTPUT_FILE

# Theoretical Performance (based on GPU model)
echo "=== THEORETICAL PEAK PERFORMANCE ===" | tee -a $OUTPUT_FILE
echo "GPU Model: $GPU_NAME" | tee -a $OUTPUT_FILE

# Detect GPU architecture and show appropriate specs
if [[ "$GPU_NAME" == *"A100"* ]]; then
    echo "Architecture: Ampere (GA100)" | tee -a $OUTPUT_FILE
    echo "FP64: 9.7 TFLOPS (19.5 with Tensor)" | tee -a $OUTPUT_FILE
    echo "FP32: 19.5 TFLOPS" | tee -a $OUTPUT_FILE
    echo "TF32 Tensor: 156 TFLOPS" | tee -a $OUTPUT_FILE
    echo "FP16/BF16 Tensor: 312 TFLOPS" | tee -a $OUTPUT_FILE
    echo "INT8 Tensor: 624 TOPS" | tee -a $OUTPUT_FILE
elif [[ "$GPU_NAME" == *"H100"* ]]; then
    echo "Architecture: Hopper (GH100)" | tee -a $OUTPUT_FILE
    echo "FP64: 34 TFLOPS (67 with Tensor)" | tee -a $OUTPUT_FILE
    echo "FP32: 67 TFLOPS" | tee -a $OUTPUT_FILE
    echo "TF32 Tensor: 989 TFLOPS" | tee -a $OUTPUT_FILE
    echo "FP16/BF16 Tensor: 1979 TFLOPS" | tee -a $OUTPUT_FILE
    echo "FP8 Tensor: 3958 TFLOPS" | tee -a $OUTPUT_FILE
elif [[ "$GPU_NAME" == *"A6000"* ]] || [[ "$GPU_NAME" == *"RTX"* ]]; then
    echo "Architecture: Ampere (GA102)" | tee -a $OUTPUT_FILE
    echo "FP32: ~40 TFLOPS" | tee -a $OUTPUT_FILE
    echo "RT Cores: 2nd Generation" | tee -a $OUTPUT_FILE
    echo "Tensor Cores: 3rd Generation" | tee -a $OUTPUT_FILE
elif [[ "$GPU_NAME" == *"V100"* ]]; then
    echo "Architecture: Volta (GV100)" | tee -a $OUTPUT_FILE
    echo "FP64: 7.8 TFLOPS" | tee -a $OUTPUT_FILE
    echo "FP32: 15.7 TFLOPS" | tee -a $OUTPUT_FILE
    echo "Tensor FP16: 125 TFLOPS" | tee -a $OUTPUT_FILE
else
    echo "Check manufacturer specs for details" | tee -a $OUTPUT_FILE
fi
echo "" | tee -a $OUTPUT_FILE

# MIG status (only for supported GPUs)
if [[ "$GPU_NAME" == *"A100"* ]] || [[ "$GPU_NAME" == *"A30"* ]] || [[ "$GPU_NAME" == *"H100"* ]]; then
    echo "=== MIG STATUS ===" | tee -a $OUTPUT_FILE
    mig_status=$(nvidia-smi --query-gpu=mig.mode.current --format=csv,noheader)
    echo "MIG Mode: $mig_status" | tee -a $OUTPUT_FILE
    echo "" | tee -a $OUTPUT_FILE
fi

# ECC status (for datacenter GPUs)
if [[ "$GPU_NAME" == *"A100"* ]] || [[ "$GPU_NAME" == *"V100"* ]] || [[ "$GPU_NAME" == *"H100"* ]] || [[ "$GPU_NAME" == *"A30"* ]] || [[ "$GPU_NAME" == *"A40"* ]]; then
    echo "=== ECC STATUS ===" | tee -a $OUTPUT_FILE
    ecc_status=$(nvidia-smi --query-gpu=ecc.mode.current --format=csv,noheader)
    echo "ECC Mode: $ecc_status" | tee -a $OUTPUT_FILE
    echo "" | tee -a $OUTPUT_FILE
fi

# System summary
echo "=== SYSTEM SUMMARY ===" | tee -a $OUTPUT_FILE
echo "Hostname: $(hostname)" | tee -a $OUTPUT_FILE
echo "Date: $(date)" | tee -a $OUTPUT_FILE
echo "Kernel: $(uname -r)" | tee -a $OUTPUT_FILE
echo "GPU: $GPU_NAME" | tee -a $OUTPUT_FILE
echo "Total Memory: $(nvidia-smi --query-gpu=memory.total --format=csv,noheader)" | tee -a $OUTPUT_FILE
echo "Driver Version: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader)" | tee -a $OUTPUT_FILE
echo "Compute Capability: $(nvidia-smi --query-gpu=compute_cap --format=csv,noheader)" | tee -a $OUTPUT_FILE

echo "" | tee -a $OUTPUT_FILE
echo "==========================================" | tee -a $OUTPUT_FILE
echo "Report saved to: $OUTPUT_FILE"
