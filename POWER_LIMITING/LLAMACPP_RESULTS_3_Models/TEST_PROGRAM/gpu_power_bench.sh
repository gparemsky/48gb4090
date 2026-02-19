#!/bin/bash
# =============================================================================
# GPvLab GPU Power Limit Benchmark Suite
# Tests multiple model architectures across power limits
# Captures: pp t/s, tg t/s, GPU power/clocks/temp via nvidia-smi dmon
# =============================================================================

set -euo pipefail

# --- Configuration ---
LLAMA_BENCH="./llama.cpp/build/bin/llama-bench"
RESULTS_DIR="/mnt/shared/bench_results/$(date +%Y%m%d_%H%M%S)"
SHARED="/mnt/shared"

# Power limits to test (watts)
POWER_LIMITS=(450 350 250 150)

# Context sizes for prompt processing
PP_SIZES="512,2048,4096,8192,16384,32768"

# Token generation counts
TG_SIZES="128,512"

# Repetitions per test
REPS=3

# GPU IDs
GPU_IDS=(0 1)

# --- Model Definitions ---
# Format: "name|path|type|notes"
MODELS=(
    "DeepSeek-R1-Distill-70B|${SHARED}/DS70B01.gguf|reasoning|Sharded dense reasoning model"
    "Qwen2.5-72B-Q4KM|${SHARED}/qwen25-q4_k_m.gguf|dense|Standard dense autoregressive"
    "GPT-OSS-F16|${SHARED}/gpt_oss-f16.gguf|moe|MoE sparse activation model"
)

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --- Functions ---

print_banner() {
    echo ""
    echo -e "${CYAN}==============================================================${NC}"
    echo -e "${CYAN} ${BOLD}$1${NC}"
    echo -e "${CYAN}==============================================================${NC}"
    echo ""
}

print_status() {
    echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date +%H:%M:%S)] WARNING: $1${NC}"
}

print_noise_prompt() {
    local model=$1
    local watts=$2
    local status=$3
    echo ""
    echo -e "${RED}==============================================================${NC}"
    echo -e "${RED}  NOISE MEASUREMENT POINT${NC}"
    echo -e "${RED}  Model: ${model}${NC}"
    echo -e "${RED}  Power Limit: ${watts}W${NC}"
    echo -e "${RED}  Status: ${status}${NC}"
    echo -e "${RED}==============================================================${NC}"
    echo ""
}

set_power_limit() {
    local watts=$1
    print_status "Setting power limit to ${watts}W on all GPUs..."
    for gpu_id in "${GPU_IDS[@]}"; do
        sudo nvidia-smi -i "$gpu_id" -pl "$watts"
    done
    sleep 3
}

restore_power_limit() {
    print_status "Restoring power limits to 450W..."
    for gpu_id in "${GPU_IDS[@]}"; do
        sudo nvidia-smi -i "$gpu_id" -pl 450
    done
}

capture_gpu_state() {
    nvidia-smi --query-gpu=index,power.draw,clocks.gr,clocks.mem,temperature.gpu,utilization.gpu,memory.used,memory.total,fan.speed \
        --format=csv,noheader,nounits
}

start_gpu_monitor() {
    local logfile=$1
    nvidia-smi dmon -s pucm -d 1 > "$logfile" 2>&1 &
    echo $!
}

stop_gpu_monitor() {
    local pid=$1
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        wait "$pid" 2>/dev/null || true
    fi
}

run_benchmark() {
    local model_name=$1
    local model_path=$2
    local model_type=$3
    local power_limit=$4
    local output_dir=$5

    local bench_file="${output_dir}/${model_name}_${power_limit}W_bench.csv"
    local monitor_file="${output_dir}/${model_name}_${power_limit}W_gpumon.txt"
    local summary_file="${output_dir}/${model_name}_${power_limit}W_summary.txt"

    print_banner "BENCHMARKING: ${model_name} @ ${power_limit}W"

    echo -e "${BOLD}Model:${NC}       $model_name"
    echo -e "${BOLD}Type:${NC}        $model_type"
    echo -e "${BOLD}Path:${NC}        $model_path"
    echo -e "${BOLD}Power Limit:${NC} ${power_limit}W"
    echo -e "${BOLD}PP sizes:${NC}    ${PP_SIZES}"
    echo -e "${BOLD}TG sizes:${NC}    ${TG_SIZES}"
    echo -e "${BOLD}Reps:${NC}        ${REPS}"
    echo ""

    # Pre-bench GPU state
    echo "=== PRE-BENCH GPU STATE ===" > "$summary_file"
    capture_gpu_state >> "$summary_file"
    echo "" >> "$summary_file"

    # Noise measurement - IDLE
    print_noise_prompt "$model_name" "$power_limit" "IDLE - Measure noise NOW before load starts"
    echo -e "${YELLOW}Press ENTER when ready to start benchmark...${NC}"
    read -r

    # Start GPU monitoring
    print_status "Starting GPU monitor..."
    local monitor_pid
    monitor_pid=$(start_gpu_monitor "$monitor_file")

    # Run llama-bench
    print_status "Running llama-bench..."
    echo ""

    local bench_start
    bench_start=$(date +%s)

    $LLAMA_BENCH \
        -m "$model_path" \
        -ngl 99 \
        -fa 1 \
        -p "$PP_SIZES" \
        -n "$TG_SIZES" \
        -r "$REPS" \
        -o csv 2>&1 | tee "$bench_file"

    local bench_end
    bench_end=$(date +%s)
    local bench_duration=$(( bench_end - bench_start ))

    echo ""
    print_status "Benchmark completed in ${bench_duration}s"

    # Noise measurement - LOAD
    print_noise_prompt "$model_name" "$power_limit" "LOAD JUST ENDED - Measure peak noise NOW"
    echo -e "${YELLOW}Press ENTER when noise captured...${NC}"
    read -r

    # Stop GPU monitoring
    stop_gpu_monitor "$monitor_pid"

    # Post-bench GPU state
    echo "=== POST-BENCH GPU STATE ===" >> "$summary_file"
    capture_gpu_state >> "$summary_file"
    echo "" >> "$summary_file"
    echo "Benchmark duration: ${bench_duration}s" >> "$summary_file"

    # Parse GPU monitor stats
    echo "" >> "$summary_file"
    echo "=== GPU MONITOR STATS ===" >> "$summary_file"
    if [[ -f "$monitor_file" ]]; then
        awk '!/^#/ && NF>5 {
            power+=$2; temp+=$3; sm+=$4; n++
            if($2>mp) mp=$2
            if($3>mt) mt=$3
            if($4>ms) ms=$4
        } END {
            if(n>0) {
                printf "Avg Power: %.1fW | Max Power: %.1fW\n", power/n, mp
                printf "Avg Temp: %.1fC | Max Temp: %.1fC\n", temp/n, mt
                printf "Avg SM Util: %.1f%% | Max SM Util: %.1f%%\n", sm/n, ms
            }
        }' "$monitor_file" | tee -a "$summary_file"
    fi

    print_status "Results saved to ${output_dir}/"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================

print_banner "GPvLab Power Limit Benchmark Suite"

echo -e "${BOLD}Pre-flight checks...${NC}"

# Check llama-bench
if [[ ! -x "$LLAMA_BENCH" ]]; then
    echo -e "${RED}ERROR: llama-bench not found at ${LLAMA_BENCH}${NC}"
    exit 1
fi
print_status "llama-bench: OK"

# Check nvidia-smi
if ! command -v nvidia-smi &>/dev/null; then
    echo -e "${RED}ERROR: nvidia-smi not found${NC}"
    exit 1
fi
print_status "nvidia-smi: OK"

# Check models exist
for model_entry in "${MODELS[@]}"; do
    IFS='|' read -r name path type notes <<< "$model_entry"
    if [[ ! -f "$path" ]]; then
        echo -e "${RED}ERROR: Model not found: ${path}${NC}"
        exit 1
    fi
    local_size=$(du -h "$path" | cut -f1)
    print_status "Model OK: ${name} (${local_size})"
done

# Show GPU info
echo ""
echo -e "${BOLD}GPU Configuration:${NC}"
nvidia-smi --query-gpu=index,name,memory.total,power.default_limit --format=csv
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"
print_status "Results directory: ${RESULTS_DIR}"

# Save test configuration
cat > "${RESULTS_DIR}/test_config.txt" << EOF
GPvLab Power Limit Benchmark
Date: $(date)
Host: $(hostname)
Kernel: $(uname -r)
Driver: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)

GPUs:
$(nvidia-smi --query-gpu=index,name,memory.total,power.default_limit,pcie.link.gen.current,pcie.link.width.current --format=csv)

Power Limits Tested: ${POWER_LIMITS[*]}
Context Sizes (pp): ${PP_SIZES}
Generation Sizes (tg): ${TG_SIZES}
Repetitions: ${REPS}

Models:
$(for m in "${MODELS[@]}"; do echo "  $m"; done)
EOF

# --- Main Loop ---

total_tests=$(( ${#MODELS[@]} * ${#POWER_LIMITS[@]} ))
current_test=0

print_banner "Starting ${total_tests} benchmark runs"
echo -e "${BOLD}Models: ${#MODELS[@]} | Power Limits: ${#POWER_LIMITS[@]}${NC}"
echo ""
echo -e "${YELLOW}Press ENTER to begin the full suite...${NC}"
read -r

for power_limit in "${POWER_LIMITS[@]}"; do
    print_banner "=== POWER LIMIT PHASE: ${power_limit}W ==="

    set_power_limit "$power_limit"

    echo -e "${BOLD}Confirmed GPU power limits:${NC}"
    nvidia-smi --query-gpu=index,power.limit --format=csv
    echo ""

    print_status "Letting GPUs settle for 10 seconds..."
    sleep 10

    for model_entry in "${MODELS[@]}"; do
        IFS='|' read -r name path type notes <<< "$model_entry"
        current_test=$(( current_test + 1 ))

        echo -e "${CYAN}[Test ${current_test}/${total_tests}]${NC}"

        run_benchmark "$name" "$path" "$type" "$power_limit" "$RESULTS_DIR"

        # Cool down between models
        print_status "Cooling down 15 seconds between models..."
        sleep 15
    done
done

# --- Cleanup ---

restore_power_limit

print_banner "ALL BENCHMARKS COMPLETE"

echo -e "${BOLD}Results saved to: ${RESULTS_DIR}${NC}"
echo ""
echo "Files generated:"
ls -lh "$RESULTS_DIR"
echo ""

# Combine all bench CSVs into one master file
print_status "Generating combined results..."
combined="${RESULTS_DIR}/combined_results.csv"
first=true
for f in "${RESULTS_DIR}"/*_bench.csv; do
    if [[ -f "$f" ]]; then
        basename_f=$(basename "$f" _bench.csv)
        if $first; then
            head -1 "$f" | sed 's/^/source,/' > "$combined"
            first=false
        fi
        tail -n +2 "$f" | while IFS= read -r line; do
            echo "${basename_f},${line}"
        done >> "$combined"
    fi
done

if [[ -f "$combined" ]]; then
    print_status "Combined CSV: ${combined}"
    echo ""
    echo -e "${BOLD}Preview of combined results:${NC}"
    head -5 "$combined"
fi

echo ""
echo -e "${GREEN}Done. Power limits restored to 450W.${NC}"
echo -e "${GREEN}Remember to record your noise measurements in the summary files!${NC}"
