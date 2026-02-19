# GPU Benchmark Comparison Report
Generated: Thu Sep  4 12:25:41 PM EDT 2025

## report-A6000_24GB-mistral_small3_2_latest.txt
```
2025-09-04 11:42:00
GPU: A6000-24GB
Model: mistral-small3.2:latest

| GPU | Model | Prompt Tokens | PP/s | TTFT | Generated Tokens | TG/s | Duration |
| --- | ----- | ------------- | ---- | ---- | ---------------- | ---- | -------- |
| A6000-24GB | mistral-small3.2:latest | 469 | 33.07 | 14.18 | 909 | 8.87 | 116.65 |
```

## report-A6000_24GB-qwen3_coder_latest.txt
```
2025-09-04 11:36:19
GPU: A6000-24GB
Model: qwen3-coder:latest

| GPU | Model | Prompt Tokens | PP/s | TTFT | Generated Tokens | TG/s | Duration |
| --- | ----- | ------------- | ---- | ---- | ---------------- | ---- | -------- |
| A6000-24GB | qwen3-coder:latest | 488 | 1646.93 | 0.30 | 524 | 98.12 | 5.64 |
| A6000-24GB | qwen3-coder:latest | 743 | 1576.62 | 0.47 | 807 | 96.32 | 8.85 |
| A6000-24GB | qwen3-coder:latest | 1176 | 1590.68 | 0.74 | 480 | 95.29 | 5.78 |
| A6000-24GB | qwen3-coder:latest | 1896 | 1673.67 | 1.13 | 728 | 91.54 | 9.09 |
| A6000-24GB | qwen3-coder:latest | 3156 | 1538.47 | 2.05 | 1101 | 84.70 | 15.05 |
| A6000-24GB | qwen3-coder:latest | 4096 | 1521.40 | 2.69 | 1709 | 84.65 | 22.88 |
| A6000-24GB | qwen3-coder:latest | 4096 | 1504.05 | 2.72 | 1332 | 84.42 | 18.50 |
| A6000-24GB | qwen3-coder:latest | 4096 | 1490.02 | 2.75 | 332 | 84.34 | 6.69 |
| A6000-24GB | qwen3-coder:latest | 4096 | 1475.33 | 2.78 | 1530 | 84.37 | 20.91 |
| A6000-24GB | qwen3-coder:latest | 0 | 0.00 | 136.72 | 0 | 0.00 | 136.72 |

Total duration: 5m40s
```

## report-A6000_48GB-deepseek_r1_70b.txt
```
2025-09-04 12:02:35
GPU: A6000-48GB
Model: deepseek-r1:70b

| GPU | Model | Prompt Tokens | PP/s | TTFT | Generated Tokens | TG/s | Duration |
| --- | ----- | ------------- | ---- | ---- | ---------------- | ---- | -------- |
| A6000-48GB | deepseek-r1:70b | 471 | 397.37 | 1.19 | 1235 | 12.35 | 101.18 |
| A6000-48GB | deepseek-r1:70b | 724 | 470.81 | 1.54 | 1302 | 12.27 | 107.64 |
| A6000-48GB | deepseek-r1:70b | 1144 | 474.07 | 2.41 | 902 | 11.93 | 78.04 |
| A6000-48GB | deepseek-r1:70b | 1841 | 464.12 | 3.97 | 922 | 11.77 | 82.29 |
| A6000-48GB | deepseek-r1:70b | 3066 | 447.38 | 6.85 | 1050 | 11.39 | 99.05 |
| A6000-48GB | deepseek-r1:70b | 4096 | 426.98 | 9.59 | 847 | 11.33 | 84.35 |
| A6000-48GB | deepseek-r1:70b | 4096 | 426.44 | 9.61 | 1487 | 11.32 | 140.98 |
| A6000-48GB | deepseek-r1:70b | 4096 | 426.19 | 9.61 | 1260 | 11.32 | 120.90 |
| A6000-48GB | deepseek-r1:70b | 4096 | 424.61 | 9.65 | 1303 | 11.32 | 124.72 |
| A6000-48GB | deepseek-r1:70b | 4096 | 423.30 | 9.68 | 1011 | 11.33 | 98.92 |

Total duration: 18m48s
```

## report-A6000_48GB-llama3_1_70b.txt
```
2025-09-04 11:51:55
GPU: A6000-48GB
Model: llama3.1:70b

| GPU | Model | Prompt Tokens | PP/s | TTFT | Generated Tokens | TG/s | Duration |
| --- | ----- | ------------- | ---- | ---- | ---------------- | ---- | -------- |
| A6000-48GB | llama3.1:70b | 483 | 489.28 | 0.99 | 732 | 12.50 | 59.55 |
| A6000-48GB | llama3.1:70b | 736 | 481.42 | 1.53 | 598 | 12.41 | 49.70 |
| A6000-48GB | llama3.1:70b | 1156 | 474.54 | 2.44 | 545 | 11.99 | 47.88 |
| A6000-48GB | llama3.1:70b | 1853 | 466.74 | 3.97 | 523 | 11.84 | 48.16 |
| A6000-48GB | llama3.1:70b | 3078 | 441.07 | 6.98 | 829 | 11.42 | 79.56 |
| A6000-48GB | llama3.1:70b | 4096 | 422.53 | 9.69 | 388 | 11.35 | 43.88 |
| A6000-48GB | llama3.1:70b | 4096 | 426.80 | 9.60 | 441 | 11.35 | 48.46 |
| A6000-48GB | llama3.1:70b | 4096 | 426.26 | 9.61 | 441 | 11.35 | 48.47 |
| A6000-48GB | llama3.1:70b | 4096 | 424.92 | 9.64 | 441 | 11.35 | 48.50 |
| A6000-48GB | llama3.1:70b | 4096 | 423.41 | 9.67 | 441 | 11.35 | 48.54 |

Total duration: 10m12s
```

