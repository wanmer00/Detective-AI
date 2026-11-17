# Pipeline benchmark: before vs after

Run `pipeline_benchmark_20261117_165630`. Full production pipeline (metadata, timeline, detectors, faces, aggregation; saliency off).
Every number is computed from `predictions_before.json` / `predictions_after.json` in this folder.

* **before** = SwinV2 only, no quality gate. **after** = SwinV2 + Community Forensics family + quality gate.
* AI-positive verdicts: ai_likely, ai_edited. Not-AI verdicts: not_ai, authentic_likely, manipulated_possible. Inconclusive is an abstention: it counts as a miss in recall/FNR, never as a hit.
* `false real` = AI image reported with a not-AI verdict (the dangerous error). `accuracy` = exact expected verdict class (REAL→not_ai/authentic, AI→ai_likely/ai_edited, MANUALLY_EDITED→manipulated_possible).

## all originals

| Config | N (AI/not-AI) | TP | False real | FN inconcl. | FP | TN | Inconcl. | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | 54 (19/35) | 13 | 4 | 2 | 0 | 29 | 8 | 0.593 | 1.0 | 0.684 | 0.813 | 0.0 | 0.316 |
| after | 54 (19/35) | 15 | 1 | 3 | 1 | 27 | 10 | 0.574 | 0.938 | 0.789 | 0.857 | 0.029 | 0.211 |

Confusion matrix (rows = ground truth, columns = verdict):

| Config | Ground truth | ai_likely | ai_edited | authentic_likely | not_ai | manipulated_possible | inconclusive |
|---|---|---|---|---|---|---|---|
| before | AI_EDITED | 0 | 0 | 0 | 1 | 0 | 0 |
| before | AI_GENERATED | 13 | 0 | 0 | 3 | 0 | 2 |
| before | MANUALLY_EDITED | 0 | 0 | 0 | 9 | 0 | 2 |
| before | REAL | 0 | 0 | 1 | 18 | 1 | 4 |
| after | AI_EDITED | 0 | 0 | 0 | 1 | 0 | 0 |
| after | AI_GENERATED | 15 | 0 | 0 | 0 | 0 | 3 |
| after | MANUALLY_EDITED | 0 | 0 | 0 | 10 | 0 | 1 |
| after | REAL | 1 | 0 | 1 | 15 | 1 | 6 |

## independent of model selection (user batch + regression)

| Config | N (AI/not-AI) | TP | False real | FN inconcl. | FP | TN | Inconcl. | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | 24 (9/15) | 5 | 4 | 0 | 0 | 12 | 3 | 0.667 | 1.0 | 0.556 | 0.714 | 0.0 | 0.444 |
| after | 24 (9/15) | 5 | 1 | 3 | 1 | 7 | 10 | 0.5 | 0.833 | 0.556 | 0.667 | 0.067 | 0.444 |

Confusion matrix (rows = ground truth, columns = verdict):

| Config | Ground truth | ai_likely | ai_edited | authentic_likely | not_ai | manipulated_possible | inconclusive |
|---|---|---|---|---|---|---|---|
| before | AI_EDITED | 0 | 0 | 0 | 1 | 0 | 0 |
| before | AI_GENERATED | 5 | 0 | 0 | 3 | 0 | 0 |
| before | MANUALLY_EDITED | 0 | 0 | 0 | 1 | 0 | 0 |
| before | REAL | 0 | 0 | 1 | 10 | 0 | 3 |
| after | AI_EDITED | 0 | 0 | 0 | 1 | 0 | 0 |
| after | AI_GENERATED | 5 | 0 | 0 | 0 | 0 | 3 |
| after | MANUALLY_EDITED | 0 | 0 | 0 | 0 | 0 | 1 |
| after | REAL | 1 | 0 | 1 | 6 | 0 | 6 |

## eval_set (used to pick SwinV2: biased)

| Config | N (AI/not-AI) | TP | False real | FN inconcl. | FP | TN | Inconcl. | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | 20 (10/10) | 8 | 0 | 2 | 0 | 9 | 3 | 0.8 | 1.0 | 0.8 | 0.889 | 0.0 | 0.2 |
| after | 20 (10/10) | 10 | 0 | 0 | 0 | 10 | 0 | 0.95 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |

Confusion matrix (rows = ground truth, columns = verdict):

| Config | Ground truth | ai_likely | ai_edited | authentic_likely | not_ai | manipulated_possible | inconclusive |
|---|---|---|---|---|---|---|---|
| before | AI_GENERATED | 8 | 0 | 0 | 0 | 0 | 2 |
| before | REAL | 0 | 0 | 0 | 8 | 1 | 1 |
| after | AI_GENERATED | 10 | 0 | 0 | 0 | 0 | 0 |
| after | REAL | 0 | 0 | 0 | 9 | 1 | 0 |

## re-compressed JPEG q70

| Config | N (AI/not-AI) | TP | False real | FN inconcl. | FP | TN | Inconcl. | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | 42 (18/24) | 6 | 7 | 5 | 0 | 22 | 7 | 0.667 | 1.0 | 0.333 | 0.5 | 0.0 | 0.667 |
| after | 42 (18/24) | 10 | 0 | 8 | 0 | 0 | 32 | 0.238 | 1.0 | 0.556 | 0.714 | 0.0 | 0.444 |

Confusion matrix (rows = ground truth, columns = verdict):

| Config | Ground truth | ai_likely | ai_edited | authentic_likely | not_ai | manipulated_possible | inconclusive |
|---|---|---|---|---|---|---|---|
| before | AI_GENERATED | 6 | 0 | 0 | 7 | 0 | 5 |
| before | REAL | 0 | 0 | 0 | 22 | 0 | 2 |
| after | AI_GENERATED | 10 | 0 | 0 | 0 | 0 | 8 |
| after | REAL | 0 | 0 | 0 | 0 | 0 | 24 |

## messenger-like 320 px + JPEG q85

| Config | N (AI/not-AI) | TP | False real | FN inconcl. | FP | TN | Inconcl. | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | 42 (18/24) | 7 | 6 | 5 | 0 | 19 | 10 | 0.619 | 1.0 | 0.389 | 0.56 | 0.0 | 0.611 |
| after | 42 (18/24) | 8 | 0 | 10 | 1 | 0 | 33 | 0.19 | 0.889 | 0.444 | 0.593 | 0.042 | 0.556 |

Confusion matrix (rows = ground truth, columns = verdict):

| Config | Ground truth | ai_likely | ai_edited | authentic_likely | not_ai | manipulated_possible | inconclusive |
|---|---|---|---|---|---|---|---|
| before | AI_GENERATED | 7 | 0 | 0 | 6 | 0 | 5 |
| before | REAL | 0 | 0 | 0 | 19 | 0 | 5 |
| after | AI_GENERATED | 8 | 0 | 0 | 0 | 0 | 10 |
| after | REAL | 1 | 0 | 0 | 0 | 0 | 23 |

## resized to 512 px

| Config | N (AI/not-AI) | TP | False real | FN inconcl. | FP | TN | Inconcl. | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | 42 (18/24) | 11 | 3 | 4 | 0 | 19 | 9 | 0.714 | 1.0 | 0.611 | 0.759 | 0.0 | 0.389 |
| after | 42 (18/24) | 14 | 0 | 4 | 1 | 20 | 7 | 0.81 | 0.933 | 0.778 | 0.848 | 0.042 | 0.222 |

Confusion matrix (rows = ground truth, columns = verdict):

| Config | Ground truth | ai_likely | ai_edited | authentic_likely | not_ai | manipulated_possible | inconclusive |
|---|---|---|---|---|---|---|---|
| before | AI_GENERATED | 11 | 0 | 0 | 3 | 0 | 4 |
| before | REAL | 0 | 0 | 0 | 19 | 0 | 5 |
| after | AI_GENERATED | 14 | 0 | 0 | 0 | 0 | 4 |
| after | REAL | 1 | 0 | 0 | 20 | 0 | 3 |

## all degraded variants

| Config | N (AI/not-AI) | TP | False real | FN inconcl. | FP | TN | Inconcl. | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | 126 (54/72) | 24 | 16 | 14 | 0 | 60 | 26 | 0.667 | 1.0 | 0.444 | 0.615 | 0.0 | 0.556 |
| after | 126 (54/72) | 32 | 0 | 22 | 2 | 20 | 72 | 0.413 | 0.941 | 0.593 | 0.727 | 0.028 | 0.407 |

Confusion matrix (rows = ground truth, columns = verdict):

| Config | Ground truth | ai_likely | ai_edited | authentic_likely | not_ai | manipulated_possible | inconclusive |
|---|---|---|---|---|---|---|---|
| before | AI_GENERATED | 24 | 0 | 0 | 16 | 0 | 14 |
| before | REAL | 0 | 0 | 0 | 60 | 0 | 12 |
| after | AI_GENERATED | 32 | 0 | 0 | 0 | 0 | 22 |
| after | REAL | 2 | 0 | 0 | 20 | 0 | 50 |

## Photoshop-style manual edits (edit_set)

| Config | N (AI/not-AI) | TP | False real | FN inconcl. | FP | TN | Inconcl. | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | 10 (0/10) | 0 | 0 | 0 | 0 | 8 | 2 | 0.0 | None | None | None | 0.0 | None |
| after | 10 (0/10) | 0 | 0 | 0 | 0 | 10 | 0 | 0.0 | None | None | None | 0.0 | None |

Confusion matrix (rows = ground truth, columns = verdict):

| Config | Ground truth | ai_likely | ai_edited | authentic_likely | not_ai | manipulated_possible | inconclusive |
|---|---|---|---|---|---|---|---|
| before | MANUALLY_EDITED | 0 | 0 | 0 | 8 | 0 | 2 |
| after | MANUALLY_EDITED | 0 | 0 | 0 | 10 | 0 | 0 |

## user-batch edited images (AI_EDITED + MANUALLY_EDITED)

| Config | N (AI/not-AI) | TP | False real | FN inconcl. | FP | TN | Inconcl. | Accuracy | Precision | Recall | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| before | 2 (1/1) | 0 | 1 | 0 | 0 | 1 | 0 | 0.0 | None | 0.0 | None | 0.0 | 1.0 |
| after | 2 (1/1) | 0 | 1 | 0 | 0 | 0 | 1 | 0.0 | None | 0.0 | None | 0.0 | 1.0 |

Confusion matrix (rows = ground truth, columns = verdict):

| Config | Ground truth | ai_likely | ai_edited | authentic_likely | not_ai | manipulated_possible | inconclusive |
|---|---|---|---|---|---|---|---|
| before | AI_EDITED | 0 | 0 | 0 | 1 | 0 | 0 |
| before | MANUALLY_EDITED | 0 | 0 | 0 | 1 | 0 | 0 |
| after | AI_EDITED | 0 | 0 | 0 | 1 | 0 | 0 |
| after | MANUALLY_EDITED | 0 | 0 | 0 | 0 | 0 | 1 |

## Regression images

| Config | ID | Variant | Verdict | Rules | Detector decisions |
|---|---|---|---|---|---|
| before | REG-001 | original | not_ai | R4b | swinv2_ai_detector=real 0.010 |
| before | REG-001 | jpeg70 | not_ai | R4b | swinv2_ai_detector=real 0.005 |
| before | REG-001 | wa320 | not_ai | R4b | swinv2_ai_detector=real 0.006 |
| before | REG-001 | small512 | not_ai | R4b | swinv2_ai_detector=real 0.010 |
| after | REG-001 | original | inconclusive | R9 | swinv2_ai_detector=real 0.010, cf_frontier=real 0.198, cf_lowq=ai 0.710 |
| after | REG-001 | jpeg70 | inconclusive | R9 | swinv2_ai_detector=real 0.005, cf_frontier=real 0.040, cf_lowq=real 0.624 |
| after | REG-001 | wa320 | inconclusive | R9 | swinv2_ai_detector=real 0.006, cf_frontier=real 0.113, cf_lowq=ai 0.672 |
| after | REG-001 | small512 | inconclusive | R9 | swinv2_ai_detector=real 0.010, cf_frontier=real 0.198, cf_lowq=ai 0.710 |
