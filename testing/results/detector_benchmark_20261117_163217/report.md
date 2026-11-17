# Detector benchmark

Run detector_benchmark_20261117_163217. Every number is computed from `raw_scores.json`. Recall counts abstentions (SwinV2 'uncertain'/'unreliable') as misses; `abstain` is shown separately.

## ALL original images

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 54 (19/35) | 11 | 4 | 0 | 28 | 11 | 0.722 | 1.0 | 0.579 | 0.733 | 0.0 | 0.421 |
| cf_frontier | 54 (19/35) | 18 | 1 | 2 | 33 | 0 | 0.944 | 0.9 | 0.947 | 0.923 | 0.057 | 0.053 |
| cf_lowq | 54 (19/35) | 18 | 1 | 3 | 32 | 0 | 0.926 | 0.857 | 0.947 | 0.9 | 0.086 | 0.053 |
| cf_vit_base | 54 (19/35) | 10 | 9 | 0 | 35 | 0 | 0.833 | 1.0 | 0.526 | 0.69 | 0.0 | 0.474 |

## batch / jpeg70

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 21 (7/14) | 1 | 4 | 0 | 13 | 3 | 0.667 | 1.0 | 0.143 | 0.25 | 0.0 | 0.857 |
| cf_frontier | 21 (7/14) | 6 | 1 | 2 | 12 | 0 | 0.857 | 0.75 | 0.857 | 0.8 | 0.143 | 0.143 |
| cf_lowq | 21 (7/14) | 7 | 0 | 2 | 12 | 0 | 0.905 | 0.778 | 1.0 | 0.875 | 0.143 | 0.0 |
| cf_vit_base | 21 (7/14) | 0 | 7 | 0 | 14 | 0 | 0.667 | None | 0.0 | None | 0.0 | 1.0 |

## batch / original

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 23 (8/15) | 3 | 3 | 0 | 12 | 5 | 0.652 | 1.0 | 0.375 | 0.545 | 0.0 | 0.625 |
| cf_frontier | 23 (8/15) | 8 | 0 | 2 | 13 | 0 | 0.913 | 0.8 | 1.0 | 0.889 | 0.133 | 0.0 |
| cf_lowq | 23 (8/15) | 7 | 1 | 2 | 13 | 0 | 0.87 | 0.778 | 0.875 | 0.824 | 0.133 | 0.125 |
| cf_vit_base | 23 (8/15) | 2 | 6 | 0 | 15 | 0 | 0.739 | 1.0 | 0.25 | 0.4 | 0.0 | 0.75 |

## batch / small512

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 21 (7/14) | 3 | 2 | 0 | 11 | 5 | 0.667 | 1.0 | 0.429 | 0.6 | 0.0 | 0.571 |
| cf_frontier | 21 (7/14) | 6 | 1 | 2 | 12 | 0 | 0.857 | 0.75 | 0.857 | 0.8 | 0.143 | 0.143 |
| cf_lowq | 21 (7/14) | 7 | 0 | 2 | 12 | 0 | 0.905 | 0.778 | 1.0 | 0.875 | 0.143 | 0.0 |
| cf_vit_base | 21 (7/14) | 2 | 5 | 0 | 14 | 0 | 0.762 | 1.0 | 0.286 | 0.444 | 0.0 | 0.714 |

## batch / wa320

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 21 (7/14) | 1 | 4 | 0 | 11 | 5 | 0.571 | 1.0 | 0.143 | 0.25 | 0.0 | 0.857 |
| cf_frontier | 21 (7/14) | 1 | 6 | 2 | 12 | 0 | 0.619 | 0.333 | 0.143 | 0.2 | 0.143 | 0.857 |
| cf_lowq | 21 (7/14) | 2 | 5 | 3 | 11 | 0 | 0.619 | 0.4 | 0.286 | 0.333 | 0.214 | 0.714 |
| cf_vit_base | 21 (7/14) | 0 | 7 | 1 | 13 | 0 | 0.619 | 0.0 | 0.0 | 0.0 | 0.071 | 1.0 |

## edits / original

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 10 (0/10) | 0 | 0 | 0 | 8 | 2 | 0.8 | None | None | None | 0.0 | None |
| cf_frontier | 10 (0/10) | 0 | 0 | 0 | 10 | 0 | 1.0 | None | None | None | 0.0 | None |
| cf_lowq | 10 (0/10) | 0 | 0 | 0 | 10 | 0 | 1.0 | None | None | None | 0.0 | None |
| cf_vit_base | 10 (0/10) | 0 | 0 | 0 | 10 | 0 | 1.0 | None | None | None | 0.0 | None |

## eval / jpeg70

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 20 (10/10) | 5 | 2 | 0 | 9 | 4 | 0.7 | 1.0 | 0.5 | 0.667 | 0.0 | 0.5 |
| cf_frontier | 20 (10/10) | 10 | 0 | 0 | 10 | 0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| cf_lowq | 20 (10/10) | 10 | 0 | 0 | 10 | 0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| cf_vit_base | 20 (10/10) | 7 | 3 | 0 | 10 | 0 | 0.85 | 1.0 | 0.7 | 0.824 | 0.0 | 0.3 |

## eval / original

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 20 (10/10) | 8 | 0 | 0 | 8 | 4 | 0.8 | 1.0 | 0.8 | 0.889 | 0.0 | 0.2 |
| cf_frontier | 20 (10/10) | 10 | 0 | 0 | 10 | 0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| cf_lowq | 20 (10/10) | 10 | 0 | 1 | 9 | 0 | 0.95 | 0.909 | 1.0 | 0.952 | 0.1 | 0.0 |
| cf_vit_base | 20 (10/10) | 8 | 2 | 0 | 10 | 0 | 0.9 | 1.0 | 0.8 | 0.889 | 0.0 | 0.2 |

## eval / small512

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 20 (10/10) | 8 | 0 | 0 | 8 | 4 | 0.8 | 1.0 | 0.8 | 0.889 | 0.0 | 0.2 |
| cf_frontier | 20 (10/10) | 9 | 1 | 0 | 10 | 0 | 0.95 | 1.0 | 0.9 | 0.947 | 0.0 | 0.1 |
| cf_lowq | 20 (10/10) | 9 | 1 | 0 | 10 | 0 | 0.95 | 1.0 | 0.9 | 0.947 | 0.0 | 0.1 |
| cf_vit_base | 20 (10/10) | 7 | 3 | 0 | 10 | 0 | 0.85 | 1.0 | 0.7 | 0.824 | 0.0 | 0.3 |

## eval / wa320

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 20 (10/10) | 6 | 1 | 0 | 8 | 5 | 0.7 | 1.0 | 0.6 | 0.75 | 0.0 | 0.4 |
| cf_frontier | 20 (10/10) | 8 | 2 | 0 | 10 | 0 | 0.9 | 1.0 | 0.8 | 0.889 | 0.0 | 0.2 |
| cf_lowq | 20 (10/10) | 9 | 1 | 1 | 9 | 0 | 0.9 | 0.9 | 0.9 | 0.9 | 0.1 | 0.1 |
| cf_vit_base | 20 (10/10) | 3 | 7 | 0 | 10 | 0 | 0.65 | 1.0 | 0.3 | 0.462 | 0.0 | 0.7 |

## independent of model selection (batch + regression, original)

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 24 (9/15) | 3 | 4 | 0 | 12 | 5 | 0.625 | 1.0 | 0.333 | 0.5 | 0.0 | 0.667 |
| cf_frontier | 24 (9/15) | 8 | 1 | 2 | 13 | 0 | 0.875 | 0.8 | 0.889 | 0.842 | 0.133 | 0.111 |
| cf_lowq | 24 (9/15) | 8 | 1 | 2 | 13 | 0 | 0.875 | 0.8 | 0.889 | 0.842 | 0.133 | 0.111 |
| cf_vit_base | 24 (9/15) | 2 | 7 | 0 | 15 | 0 | 0.708 | 1.0 | 0.222 | 0.364 | 0.0 | 0.778 |

## regression / jpeg70

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |
| cf_frontier | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |
| cf_lowq | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |
| cf_vit_base | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |

## regression / original

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |
| cf_frontier | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |
| cf_lowq | 1 (1/0) | 1 | 0 | 0 | 0 | 0 | 1.0 | 1.0 | 1.0 | 1.0 | None | 0.0 |
| cf_vit_base | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |

## regression / small512

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |
| cf_frontier | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |
| cf_lowq | 1 (1/0) | 1 | 0 | 0 | 0 | 0 | 1.0 | 1.0 | 1.0 | 1.0 | None | 0.0 |
| cf_vit_base | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |

## regression / wa320

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |
| cf_frontier | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |
| cf_lowq | 1 (1/0) | 1 | 0 | 0 | 0 | 0 | 1.0 | 1.0 | 1.0 | 1.0 | None | 0.0 |
| cf_vit_base | 1 (1/0) | 0 | 1 | 0 | 0 | 0 | 0.0 | None | 0.0 | None | None | 1.0 |

## robustness: jpeg70

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 42 (18/24) | 6 | 7 | 0 | 22 | 7 | 0.667 | 1.0 | 0.333 | 0.5 | 0.0 | 0.667 |
| cf_frontier | 42 (18/24) | 16 | 2 | 2 | 22 | 0 | 0.905 | 0.889 | 0.889 | 0.889 | 0.083 | 0.111 |
| cf_lowq | 42 (18/24) | 17 | 1 | 2 | 22 | 0 | 0.929 | 0.895 | 0.944 | 0.919 | 0.083 | 0.056 |
| cf_vit_base | 42 (18/24) | 7 | 11 | 0 | 24 | 0 | 0.738 | 1.0 | 0.389 | 0.56 | 0.0 | 0.611 |

## robustness: small512

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 42 (18/24) | 11 | 3 | 0 | 19 | 9 | 0.714 | 1.0 | 0.611 | 0.759 | 0.0 | 0.389 |
| cf_frontier | 42 (18/24) | 15 | 3 | 2 | 22 | 0 | 0.881 | 0.882 | 0.833 | 0.857 | 0.083 | 0.167 |
| cf_lowq | 42 (18/24) | 17 | 1 | 2 | 22 | 0 | 0.929 | 0.895 | 0.944 | 0.919 | 0.083 | 0.056 |
| cf_vit_base | 42 (18/24) | 9 | 9 | 0 | 24 | 0 | 0.786 | 1.0 | 0.5 | 0.667 | 0.0 | 0.5 |

## robustness: wa320

| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| swinv2 (production) | 42 (18/24) | 7 | 6 | 0 | 19 | 10 | 0.619 | 1.0 | 0.389 | 0.56 | 0.0 | 0.611 |
| cf_frontier | 42 (18/24) | 9 | 9 | 2 | 22 | 0 | 0.738 | 0.818 | 0.5 | 0.621 | 0.083 | 0.5 |
| cf_lowq | 42 (18/24) | 12 | 6 | 4 | 20 | 0 | 0.762 | 0.75 | 0.667 | 0.706 | 0.167 | 0.333 |
| cf_vit_base | 42 (18/24) | 3 | 15 | 1 | 23 | 0 | 0.619 | 0.75 | 0.167 | 0.273 | 0.042 | 0.833 |
