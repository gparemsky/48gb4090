#!/bin/bash

# Model selector for different VRAM configurations

echo "=========================================="
echo "Ollama Model Selector for GPU Testing"
echo "=========================================="

# Function to get model size
get_model_size() {
    local model=$1
    ollama list | grep "$model" | awk '{print $3, $4}'
}

# Function to load a model
load_model() {
    local model=$1
    echo "Loading model: $model"
    echo "This will pull the model if not already available..."
    
    # Run a simple prompt to load the model into VRAM
    ollama run "$model" "Test load" --verbose 2>&1 | head -20
    
    if [ $? -eq 0 ]; then
        echo "✓ Model $model loaded successfully"
        echo "You can now run benchmarks with this model"
    else
        echo "✗ Failed to load model $model"
    fi
}

echo ""
echo "Recommended models by VRAM size:"
echo ""
echo "=== For 24GB VRAM (RTX 3090/4090) ==="
echo "  • qwen3-coder:latest (18 GB) - Good coding model"
echo "  • mistral-small3.2:latest (15 GB) - Fast, efficient"
echo "  • qwen2.5-coder:32b (19 GB) - Latest Qwen coder"
echo "  • gemma3:27b (17 GB) - Google's model"
echo ""
echo "=== For 48GB VRAM (Dual 3090, A6000) ==="
echo "  • llama3.1:70b (42 GB) - Meta's latest"
echo "  • deepseek-r1:70b (42 GB) - Reasoning model"
echo "  • qwen3:32b (20 GB) - Fits with room to spare"
echo ""
echo "=== For 80GB+ VRAM (A100) ==="
echo "  • gpt-oss:120b (65 GB) - Large model"
echo "  • Any of the above with larger context"
echo ""

echo "Select action:"
echo "1. Load a 24GB model"
echo "2. Load a 48GB model"
echo "3. Load a 80GB+ model"
echo "4. Check current model in memory"
echo "5. List all available models"
echo "6. Pull a new model from Ollama library"
echo "0. Exit"

read -p "Choice: " choice

case $choice in
    1)
        echo ""
        echo "Select 24GB model to load:"
        echo "1. qwen3-coder:latest"
        echo "2. mistral-small3.2:latest"
        echo "3. qwen2.5-coder:32b"
        echo "4. gemma3:27b"
        read -p "Model choice: " model_choice
        
        case $model_choice in
            1) load_model "qwen3-coder:latest" ;;
            2) load_model "mistral-small3.2:latest" ;;
            3) load_model "qwen2.5-coder:32b" ;;
            4) load_model "gemma3:27b" ;;
            *) echo "Invalid choice" ;;
        esac
        ;;
        
    2)
        echo ""
        echo "Select 48GB model to load:"
        echo "1. llama3.1:70b"
        echo "2. deepseek-r1:70b"
        echo "3. qwen3:32b"
        read -p "Model choice: " model_choice
        
        case $model_choice in
            1) load_model "llama3.1:70b" ;;
            2) load_model "deepseek-r1:70b" ;;
            3) load_model "qwen3:32b" ;;
            *) echo "Invalid choice" ;;
        esac
        ;;
        
    3)
        echo ""
        echo "Loading large model: gpt-oss:120b"
        load_model "gpt-oss:120b"
        ;;
        
    4)
        echo ""
        echo "Checking GPU memory usage..."
        nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv
        echo ""
        echo "Recent Ollama activity:"
        ps aux | grep ollama | grep -v grep
        ;;
        
    5)
        echo ""
        echo "Available models:"
        ollama list
        ;;
        
    6)
        echo ""
        echo "Enter model name to pull (e.g., llama3.2:3b):"
        read -p "Model: " model_name
        ollama pull "$model_name"
        ;;
        
    0)
        echo "Exiting..."
        exit 0
        ;;
        
    *)
        echo "Invalid choice"
        ;;
esac

echo ""
echo "Tip: After loading a model, run ./run_gpu_benchmark.sh to test performance"