#!/bin/bash

# Enhanced GPU Benchmark Runner
# For testing GPUs with higher context lengths and comparison analysis

echo "=========================================="
echo "Enhanced GPU LLM Benchmark Suite"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Activate virtual environment
cd /home/gparemsky/prompt-test
source prompt-test/bin/activate 2>/dev/null || echo "Note: Virtual environment not found"

# Check if enhanced test files exist
check_setup() {
    echo -e "\n${YELLOW}Checking setup...${NC}"
    
    # Check for context prompts
    if [ ! -d "context_prompts" ]; then
        echo -e "${YELLOW}Context prompts not found. Generating...${NC}"
        python generate_large_prompts.py
    else
        echo -e "${GREEN}✓ Context prompts found${NC}"
    fi
    
    # Check for matplotlib (needed for comparison plots)
    python -c "import matplotlib" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}matplotlib not installed (needed for plots)${NC}"
        echo "Install with: pip install matplotlib"
    fi
    
    # Check Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama server is running${NC}"
    else
        echo -e "${RED}✗ Ollama server is not running${NC}"
        echo "Please start Ollama with: ollama serve"
        return 1
    fi
    
    return 0
}

# Function to run 24GB baseline test
run_24gb_baseline() {
    local model=$1
    echo -e "\n${BLUE}Running 24GB Baseline Test${NC}"
    echo "Model: $model"
    echo "Categories: small, medium"
    
    python test_advanced_gpu.py "RTX4090-24GB" "$model" --categories small medium
}

# Function to run 48GB test
run_48gb_test() {
    local model=$1
    echo -e "\n${BLUE}Running 48GB Enhanced Test${NC}"
    echo "Model: $model"
    echo "Categories: small, medium, large"
    
    python test_advanced_gpu.py "RTX4090-48GB" "$model" --categories small medium large
}

# Function to run extreme test (48GB only)
run_extreme_test() {
    local model=$1
    echo -e "\n${BLUE}Running Extreme Context Test (48GB)${NC}"
    echo "Model: $model"
    echo "Testing maximum context lengths..."
    
    python test_advanced_gpu.py "RTX4090-48GB" "$model" --categories large extreme --cooling 30
}

# Function to analyze results
analyze_results() {
    echo -e "\n${YELLOW}Analyzing benchmark results...${NC}"
    python analyze_gpu_comparison.py
}

# Main menu
main_menu() {
    echo -e "\n${YELLOW}Enhanced Benchmark Options${NC}"
    echo "======================================"
    echo "1. Quick Test (current GPU, small contexts)"
    echo "2. 24GB Baseline (small + medium contexts)"
    echo "3. 48GB Standard (small + medium + large contexts)"
    echo "4. 48GB Extreme (large + extreme contexts)"
    echo "5. Run Full Comparison (24GB vs 48GB)"
    echo "6. Analyze Existing Results"
    echo "7. Generate New Context Prompts"
    echo "0. Exit"
    echo ""
    read -p "Enter your choice: " choice
    
    case $choice in
        1)
            echo -e "\n${YELLOW}Quick Test${NC}"
            read -p "Enter model name (e.g., qwen2.5-coder:32b): " model
            python test_advanced_gpu.py "QuickTest" "$model" --categories small
            ;;
            
        2)
            echo -e "\n${YELLOW}24GB Baseline Test${NC}"
            ollama list | tail -n +2 | awk '{print "  - " $1}'
            read -p "Enter model name: " model
            run_24gb_baseline "$model"
            ;;
            
        3)
            echo -e "\n${YELLOW}48GB Standard Test${NC}"
            ollama list | tail -n +2 | awk '{print "  - " $1}'
            read -p "Enter model name: " model
            run_48gb_test "$model"
            ;;
            
        4)
            echo -e "\n${YELLOW}48GB Extreme Test${NC}"
            echo -e "${RED}Warning: This will test very large contexts!${NC}"
            ollama list | tail -n +2 | awk '{print "  - " $1}'
            read -p "Enter model name: " model
            run_extreme_test "$model"
            ;;
            
        5)
            echo -e "\n${YELLOW}Full Comparison Test${NC}"
            ollama list | tail -n +2 | awk '{print "  - " $1}'
            read -p "Enter model name: " model
            
            echo -e "\n${BLUE}Phase 1: 24GB Baseline${NC}"
            run_24gb_baseline "$model"
            
            echo -e "\n${YELLOW}Cooling down for 30 seconds...${NC}"
            sleep 30
            
            echo -e "\n${BLUE}Phase 2: 48GB Enhanced${NC}"
            run_48gb_test "$model"
            
            echo -e "\n${BLUE}Phase 3: Analysis${NC}"
            analyze_results
            ;;
            
        6)
            analyze_results
            ;;
            
        7)
            echo -e "\n${YELLOW}Regenerating context prompts...${NC}"
            rm -rf context_prompts
            python generate_large_prompts.py
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

# Check GPU info
show_gpu_info() {
    echo -e "\n${YELLOW}Current GPU Configuration:${NC}"
    nvidia-smi --query-gpu=name,memory.total,memory.free,temperature.gpu --format=csv
}

# Main execution
if ! check_setup; then
    echo -e "\n${RED}Setup check failed. Please fix issues above.${NC}"
    exit 1
fi

show_gpu_info

while true; do
    main_menu
    
    echo ""
    read -p "Continue? (y/n): " continue_test
    if [ "$continue_test" != "y" ]; then
        break
    fi
done

echo -e "\n${GREEN}Benchmark session complete!${NC}"
echo "Check report_advanced_*.json files for detailed results"
echo "Check gpu_comparison_report_*.md for comparison analysis"