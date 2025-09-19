#!/bin/bash

# GPU Benchmark Script for Multiple NVIDIA GPUs
# Tests different models on various GPU configurations

echo "=========================================="
echo "GPU LLM Performance Benchmark Suite"
echo "=========================================="

# Activate virtual environment
cd /home/gparemsky/prompt-test
source prompt-test/bin/activate

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test if Ollama is running
check_ollama() {
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama server is running${NC}"
        return 0
    else
        echo -e "${RED}✗ Ollama server is not running${NC}"
        echo "Please start Ollama with: ollama serve"
        return 1
    fi
}

# Function to list available models
list_models() {
    echo -e "\n${YELLOW}Available Ollama models:${NC}"
    ollama list | tail -n +2 | awk '{print "  - " $1}'
}

# Function to run a benchmark
run_benchmark() {
    local gpu_name=$1
    local model=$2
    
    echo -e "\n${GREEN}Starting benchmark:${NC}"
    echo "  GPU: $gpu_name"
    echo "  Model: $model"
    echo "  Time: $(date)"
    
    python test_ollama_base.py "$gpu_name" "$model"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Benchmark completed successfully${NC}"
    else
        echo -e "${RED}✗ Benchmark failed${NC}"
    fi
}

# Function to run model size tests
run_size_tests() {
    local gpu_name=$1
    local size_category=$2
    
    echo -e "\n${YELLOW}Running $size_category tests on $gpu_name${NC}"
    
    case $size_category in
        "24gb")
            # Models that fit in 24GB VRAM
            echo "Testing models suitable for 24GB VRAM..."
            run_benchmark "$gpu_name" "qwen3-coder:latest"
            run_benchmark "$gpu_name" "mistral-small3.2:latest"
            run_benchmark "$gpu_name" "qwen2.5-coder:32b"
            ;;
        "48gb")
            # Models that need ~48GB VRAM
            echo "Testing models suitable for 48GB VRAM..."
            run_benchmark "$gpu_name" "llama3.1:70b"
            run_benchmark "$gpu_name" "deepseek-r1:70b"
            ;;
        "80gb")
            # Models that need 80GB+ VRAM
            echo "Testing large models..."
            run_benchmark "$gpu_name" "gpt-oss:120b"
            ;;
        *)
            echo "Unknown size category: $size_category"
            ;;
    esac
}

# Main menu
main_menu() {
    echo -e "\n${YELLOW}GPU Benchmark Configuration${NC}"
    echo "======================================"
    echo "1. Test 24GB Models (fits single 24GB GPU)"
    echo "2. Test 48GB Models (needs dual 24GB or single 48GB GPU)"
    echo "3. Test 80GB+ Models (needs dual 48GB or 80GB+ GPU)"
    echo "4. Custom benchmark (specify GPU and model)"
    echo "5. Quick test (current GPU, small model)"
    echo "6. List available models"
    echo "7. CINEMATIC MODE (Visual dashboard for recordings)"
    echo "8. DIAGNOSTIC MODE (Monochrome debug output for screenshots)"
    echo "0. Exit"
    echo ""
    read -p "Enter your choice: " choice
    
    case $choice in
        1)
            echo -e "\n${YELLOW}24GB GPU Tests${NC}"
            echo "Select GPU:"
            echo "1. RTX 3090 (24GB)"
            echo "2. RTX 4090 (24GB)"
            echo "3. A6000 (48GB running 24GB models)"
            echo "4. A100 (80GB running 24GB models)"
            read -p "Choice: " gpu_choice
            
            case $gpu_choice in
                1) gpu_name="RTX3090" ;;
                2) gpu_name="RTX4090" ;;
                3) gpu_name="A6000-24GB" ;;
                4) gpu_name="A100-24GB" ;;
                *) echo "Invalid choice"; return ;;
            esac
            
            run_size_tests "$gpu_name" "24gb"
            ;;
            
        2)
            echo -e "\n${YELLOW}48GB Configuration Tests${NC}"
            echo "Select configuration:"
            echo "1. Dual RTX 3090 (2x24GB)"
            echo "2. RTX 4090 48GB (Modded)"
            echo "3. A6000 (48GB)"
            echo "4. A100 (80GB running 48GB models)"
            echo "5. Dual RTX 4090 (2x24GB)"
            echo "6. Dual A6000 (2x48GB)"
            read -p "Choice: " gpu_choice
            
            case $gpu_choice in
                1) gpu_name="RTX3090-Dual" ;;
                2) gpu_name="RTX4090-48GB" ;;
                3) gpu_name="A6000-48GB" ;;
                4) gpu_name="A100-48GB" ;;
                5) gpu_name="RTX4090-Dual" ;;
                6) gpu_name="A6000-Dual" ;;
                *) echo "Invalid choice"; return ;;
            esac
            
            run_size_tests "$gpu_name" "48gb"
            ;;
            
        3)
            echo -e "\n${YELLOW}80GB+ GPU Tests (Large Models)${NC}"
            echo "Select high-memory configuration:"
            echo "1. A100 80GB (Single)"
            echo "2. Dual RTX 4090 48GB (2x48GB = 96GB)"
            echo "3. Dual A6000 (2x48GB = 96GB)"
            echo "4. Dual A100 (2x80GB = 160GB)"
            read -p "Choice: " gpu_choice
            
            case $gpu_choice in
                1) gpu_name="A100-80GB" ;;
                2) gpu_name="RTX4090-48GB-Dual" ;;
                3) gpu_name="A6000-48GB-Dual" ;;
                4) gpu_name="A100-80GB-Dual" ;;
                *) echo "Invalid choice"; return ;;
            esac
            
            run_size_tests "$gpu_name" "80gb"
            ;;
            
        4)
            echo -e "\n${YELLOW}Custom Benchmark${NC}"
            read -p "Enter GPU name (e.g., RTX3090): " gpu_name
            list_models
            read -p "Enter model name (e.g., qwen3:32b): " model_name
            run_benchmark "$gpu_name" "$model_name"
            ;;
            
        5)
            echo -e "\n${YELLOW}Quick Test${NC}"
            # Detect current GPU
            current_gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1 | sed 's/ /_/g')
            echo "Detected GPU: $current_gpu"
            echo "Running quick test with mistral-small3.2:latest..."
            run_benchmark "$current_gpu" "mistral-small3.2:latest"
            ;;
            
        6)
            list_models
            ;;
            
        7)
            echo -e "\n${YELLOW}═══════════════════════════════════════════${NC}"
            echo -e "${GREEN}     CINEMATIC BENCHMARK MODE${NC}"
            echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
            echo -e "${GREEN}Visual dashboard with real-time GPU metrics${NC}"
            echo -e "${GREEN}Perfect for screen recordings and demos!${NC}"
            echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
            echo ""
            echo "Select configuration:"
            echo "1. RTX 4090 48GB + Small Model (qwen3-coder)"
            echo "2. RTX 4090 48GB + Medium Model (mistral-small3.2)"
            echo "3. RTX 4090 48GB + Large Model (llama3.1:70b)"
            echo "4. RTX 4090 48GB + Custom Model"
            echo "5. Other GPU + Custom Model"
            read -p "Choice: " cine_choice
            
            case $cine_choice in
                1)
                    gpu_name="RTX4090-48GB"
                    model_name="qwen3-coder:latest"
                    ;;
                2)
                    gpu_name="RTX4090-48GB"
                    model_name="mistral-small3.2:latest"
                    ;;
                3)
                    gpu_name="RTX4090-48GB"
                    model_name="llama3.1:70b"
                    ;;
                4)
                    gpu_name="RTX4090-48GB"
                    list_models
                    read -p "Enter model name: " model_name
                    ;;
                5)
                    read -p "Enter GPU name: " gpu_name
                    list_models
                    read -p "Enter model name: " model_name
                    ;;
                *)
                    echo "Invalid choice"
                    return
                    ;;
            esac
            
            echo -e "\n${GREEN}Launching cinematic benchmark...${NC}"
            echo -e "${YELLOW}Controls:${NC}"
            echo "  • Press 'q' to quit"
            echo "  • Press 's' to skip current prompt"
            echo ""
            echo -e "${GREEN}Starting in 3 seconds...${NC}"
            sleep 3
            
            # Ensure we're in the virtual environment
            source prompt-test/bin/activate
            python cinematic_benchmark_smooth.py "$gpu_name" "$model_name"
            
            if [ $? -eq 0 ]; then
                echo -e "\n${GREEN}✓ Cinematic benchmark completed${NC}"
            else
                echo -e "\n${RED}✗ Cinematic benchmark failed${NC}"
            fi
            ;;
            
        8)
            echo -e "\n${YELLOW}───────────────────────────────────────────${NC}"
            echo -e "${GREEN}     DIAGNOSTIC BENCHMARK MODE${NC}"
            echo -e "${YELLOW}───────────────────────────────────────────${NC}"
            echo -e "Monochrome display for debugging & screenshots"
            echo -e "Shows detailed GPU metrics and LLM performance"
            echo -e "${YELLOW}───────────────────────────────────────────${NC}"
            echo ""
            echo "Select configuration:"
            echo "1. RTX 4090 48GB + Small Model (qwen3-coder)"
            echo "2. RTX 4090 48GB + Medium Model (mistral-small3.2)"
            echo "3. RTX 4090 48GB + Large Model (llama3.1:70b)"
            echo "4. RTX 4090 48GB + Custom Model"
            echo "5. Other GPU + Custom Model"
            read -p "Choice: " diag_choice
            
            case $diag_choice in
                1)
                    gpu_name="RTX4090-48GB"
                    model_name="qwen3-coder:latest"
                    ;;
                2)
                    gpu_name="RTX4090-48GB"
                    model_name="mistral-small3.2:latest"
                    ;;
                3)
                    gpu_name="RTX4090-48GB"
                    model_name="llama3.1:70b"
                    ;;
                4)
                    gpu_name="RTX4090-48GB"
                    list_models
                    read -p "Enter model name: " model_name
                    ;;
                5)
                    read -p "Enter GPU name: " gpu_name
                    list_models
                    read -p "Enter model name: " model_name
                    ;;
                *)
                    echo "Invalid choice"
                    return
                    ;;
            esac
            
            echo -e "\n${GREEN}Launching diagnostic benchmark...${NC}"
            echo "Features:"
            echo "  • Detailed GPU metrics (temp, clocks, memory bandwidth)"
            echo "  • Real-time token generation statistics"
            echo "  • Word-by-word output display"
            echo "  • Performance graphs"
            echo ""
            echo -e "${YELLOW}Controls:${NC}"
            echo "  • Press 'q' to quit"
            echo "  • Press 's' to skip current prompt"
            echo ""
            echo -e "${GREEN}Starting in 3 seconds...${NC}"
            sleep 3
            
            # Ensure we're in the virtual environment
            source prompt-test/bin/activate
            python diagnostic_benchmark.py "$gpu_name" "$model_name"
            
            if [ $? -eq 0 ]; then
                echo -e "\n${GREEN}✓ Diagnostic benchmark completed${NC}"
            else
                echo -e "\n${RED}✗ Diagnostic benchmark failed${NC}"
            fi
            ;;
            
        0)
            echo "Exiting..."
            exit 0
            ;;
            
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac
}

# Function to generate comparison report
generate_comparison() {
    echo -e "\n${YELLOW}Generating comparison report...${NC}"
    
    # Find all report files
    if ls report-*.txt 1> /dev/null 2>&1; then
        output_file="benchmark_comparison_$(date +%Y%m%d_%H%M%S).md"
        
        echo "# GPU Benchmark Comparison Report" > "$output_file"
        echo "Generated: $(date)" >> "$output_file"
        echo "" >> "$output_file"
        
        for report in report-*.txt; do
            echo "## $report" >> "$output_file"
            echo '```' >> "$output_file"
            cat "$report" >> "$output_file"
            echo '```' >> "$output_file"
            echo "" >> "$output_file"
        done
        
        echo -e "${GREEN}✓ Comparison report saved to: $output_file${NC}"
    else
        echo -e "${RED}No report files found${NC}"
    fi
}

# Check if Ollama is running
if ! check_ollama; then
    echo -e "\n${YELLOW}To start Ollama:${NC}"
    echo "  1. In a new terminal: ollama serve"
    echo "  2. Wait for it to start"
    echo "  3. Run this script again"
    exit 1
fi

# Main loop
while true; do
    main_menu
    
    echo ""
    read -p "Generate comparison report? (y/n): " gen_report
    if [ "$gen_report" = "y" ]; then
        generate_comparison
    fi
    
    echo ""
    read -p "Continue testing? (y/n): " continue_test
    if [ "$continue_test" != "y" ]; then
        break
    fi
done

echo -e "\n${GREEN}Benchmark session complete!${NC}"
echo "Check report-*.txt files for detailed results"