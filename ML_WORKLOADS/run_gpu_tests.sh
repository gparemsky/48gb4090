#!/bin/bash

echo "GPU Performance Testing Script for prompt-test"
echo "=============================================="

# Activate virtual environment
cd /home/gparemsky/prompt-test
source prompt-test/bin/activate

# Function to run a test configuration
run_test() {
    local test_name=$1
    local test_file=$2
    
    echo ""
    echo "Running test: $test_name"
    echo "---------------------------------------------"
    
    if [ -f "$test_file" ]; then
        python "$test_file"
        echo "Test completed: $test_name"
        echo "Report saved to: report-*.txt"
    else
        echo "Error: Test file $test_file not found"
    fi
}

# Main menu
echo ""
echo "Select GPU configuration to test:"
echo "1. 24GB VRAM - Single GPU"
echo "2. 24GB VRAM - Dual GPU"
echo "3. 48GB VRAM - Single GPU"
echo "4. 48GB VRAM - Dual GPU"
echo "5. Run all tests"
echo "0. Exit"
echo ""

read -p "Enter your choice (0-5): " choice

case $choice in
    1)
        run_test "24GB Single GPU" "test_24gb_single.py"
        ;;
    2)
        run_test "24GB Dual GPU" "test_24gb_dual.py"
        ;;
    3)
        run_test "48GB Single GPU" "test_48gb_single.py"
        ;;
    4)
        run_test "48GB Dual GPU" "test_48gb_dual.py"
        ;;
    5)
        echo "Running all GPU configurations..."
        run_test "24GB Single GPU" "test_24gb_single.py"
        run_test "24GB Dual GPU" "test_24gb_dual.py"
        run_test "48GB Single GPU" "test_48gb_single.py"
        run_test "48GB Dual GPU" "test_48gb_dual.py"
        echo ""
        echo "All tests completed!"
        ;;
    0)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo ""
echo "Testing complete. Check the report files for results."