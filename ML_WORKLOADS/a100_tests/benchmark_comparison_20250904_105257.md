# GPU Benchmark Comparison Report
Generated: Thu Sep  4 10:52:57 AM EDT 2025

## report-A100_24GB-mistral_small3_2_latest.txt
```
2025-09-04 10:39:57
GPU: A100-24GB
Model: mistral-small3.2:latest

| GPU | Model | Prompt Tokens | PP/s | TTFT | Generated Tokens | TG/s | Duration |
| --- | ----- | ------------- | ---- | ---- | ---------------- | ---- | -------- |
| A100-24GB | mistral-small3.2:latest | 469 | 1198.33 | 0.39 | 598 | 55.96 | 11.08 |
| A100-24GB | mistral-small3.2:latest | 724 | 1399.03 | 0.52 | 688 | 55.38 | 12.94 |
| A100-24GB | mistral-small3.2:latest | 1146 | 1465.69 | 0.78 | 649 | 51.08 | 13.49 |
| A100-24GB | mistral-small3.2:latest | 1846 | 1501.36 | 1.23 | 602 | 50.64 | 13.12 |
| A100-24GB | mistral-small3.2:latest | 3085 | 1506.42 | 2.05 | 599 | 49.46 | 14.16 |
| A100-24GB | mistral-small3.2:latest | 4096 | 1512.55 | 2.71 | 516 | 49.20 | 13.19 |
| A100-24GB | mistral-small3.2:latest | 4096 | 1505.99 | 2.72 | 568 | 49.20 | 14.26 |
| A100-24GB | mistral-small3.2:latest | 4096 | 1498.03 | 2.73 | 709 | 49.06 | 17.19 |
| A100-24GB | mistral-small3.2:latest | 4096 | 1482.03 | 2.76 | 645 | 48.97 | 15.94 |
| A100-24GB | mistral-small3.2:latest | 4096 | 1461.54 | 2.80 | 519 | 48.95 | 13.40 |

Total duration: 3m48s
```

## report-A100_24GB-qwen2_5_coder_32b.txt
```
2025-09-04 10:43:49
GPU: A100-24GB
Model: qwen2.5-coder:32b

| GPU | Model | Prompt Tokens | PP/s | TTFT | Generated Tokens | TG/s | Duration |
| --- | ----- | ------------- | ---- | ---- | ---------------- | ---- | -------- |
| A100-24GB | qwen2.5-coder:32b | 488 | 989.25 | 0.49 | 839 | 36.89 | 23.24 |
| A100-24GB | qwen2.5-coder:32b | 743 | 996.90 | 0.75 | 1261 | 36.31 | 35.47 |
| A100-24GB | qwen2.5-coder:32b | 1176 | 1016.73 | 1.16 | 1156 | 33.32 | 35.85 |
| A100-24GB | qwen2.5-coder:32b | 1896 | 1050.76 | 1.80 | 833 | 32.99 | 27.05 |
| A100-24GB | qwen2.5-coder:32b | 3156 | 1031.08 | 3.06 | 1087 | 31.88 | 37.16 |
| A100-24GB | qwen2.5-coder:32b | 4096 | 1018.62 | 4.02 | 830 | 31.87 | 30.06 |
| A100-24GB | qwen2.5-coder:32b | 4096 | 1014.94 | 4.04 | 1492 | 31.80 | 50.96 |
| A100-24GB | qwen2.5-coder:32b | 4096 | 1007.63 | 4.06 | 1139 | 31.84 | 39.83 |
| A100-24GB | qwen2.5-coder:32b | 4096 | 998.49 | 4.10 | 919 | 31.84 | 32.97 |
| A100-24GB | qwen2.5-coder:32b | 4096 | 986.21 | 4.15 | 1121 | 31.86 | 39.34 |

Total duration: 7m22s
```

## report-A100_24GB-qwen3_coder_latest.txt
```
2025-09-04 10:36:13
GPU: A100-24GB
Model: qwen3-coder:latest

| GPU | Model | Prompt Tokens | PP/s | TTFT | Generated Tokens | TG/s | Duration |
| --- | ----- | ------------- | ---- | ---- | ---------------- | ---- | -------- |
| A100-24GB | qwen3-coder:latest | 488 | 1520.12 | 0.32 | 596 | 88.91 | 7.02 |
| A100-24GB | qwen3-coder:latest | 743 | 1477.42 | 0.50 | 943 | 87.27 | 11.31 |
| A100-24GB | qwen3-coder:latest | 1176 | 1524.59 | 0.77 | 596 | 86.54 | 7.66 |
| A100-24GB | qwen3-coder:latest | 1896 | 1637.85 | 1.16 | 627 | 84.44 | 8.58 |
| A100-24GB | qwen3-coder:latest | 3156 | 1589.24 | 1.99 | 1291 | 80.40 | 18.04 |
| A100-24GB | qwen3-coder:latest | 4096 | 1605.86 | 2.55 | 642 | 81.40 | 10.44 |
| A100-24GB | qwen3-coder:latest | 4096 | 1601.81 | 2.56 | 902 | 81.28 | 13.65 |
| A100-24GB | qwen3-coder:latest | 4096 | 1589.32 | 2.58 | 375 | 81.49 | 7.18 |
| A100-24GB | qwen3-coder:latest | 4096 | 1572.07 | 2.61 | 1280 | 81.37 | 18.34 |
| A100-24GB | qwen3-coder:latest | 4096 | 1541.31 | 2.66 | 1367 | 81.22 | 19.49 |

Total duration: 3m31s
```

## report-A100_80GB-gpt_oss_120b.txt
```
2025-09-04 10:23:00
GPU: A100-80GB
Model: gpt-oss:120b

| GPU | Model | Prompt Tokens | PP/s | TTFT | Generated Tokens | TG/s | Duration |
| --- | ----- | ------------- | ---- | ---- | ---------------- | ---- | -------- |
| A100-80GB | gpt-oss:120b | 525 | 474.99 | 1.11 | 1594 | 53.72 | 30.78 |
| A100-80GB | gpt-oss:120b | 767 | 410.86 | 1.87 | 1620 | 53.59 | 32.10 |
| A100-80GB | gpt-oss:120b | 1162 | 442.25 | 2.63 | 2000 | 53.23 | 40.20 |
| A100-80GB | gpt-oss:120b | 1832 | 466.71 | 3.93 | 2000 | 52.83 | 41.78 |
| A100-80GB | gpt-oss:120b | 3007 | 489.65 | 6.14 | 2000 | 52.11 | 44.52 |
| A100-80GB | gpt-oss:120b | 4705 | 463.58 | 10.15 | 2000 | 51.50 | 48.98 |
| A100-80GB | gpt-oss:120b | 7555 | 462.55 | 16.33 | 2000 | 50.45 | 55.98 |
| A100-80GB | gpt-oss:120b | 8192 | 472.18 | 17.35 | 500 | 50.85 | 27.18 |
| A100-80GB | gpt-oss:120b | 8192 | 470.53 | 17.41 | 500 | 51.00 | 27.21 |
| A100-80GB | gpt-oss:120b | 8192 | 468.17 | 17.50 | 500 | 51.01 | 27.30 |

Total duration: 7m46s
```

