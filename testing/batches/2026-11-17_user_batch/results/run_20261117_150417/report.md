# Detective AI — evaluation report (run_20261117_150417)

All figures are computed from the predictions in `predictions.csv` of this run. Ground truth comes from `testing/manifest.csv` and was recorded before the run.

## Dataset

- Images evaluated: **23** (2 derived from other images in the set)
- Independent source images: **21** — derivatives of one original are NOT independent; see the source-weighted accuracy below.
- Categories with fewer than 5 images: C01, C02, C03, C04, C05, C06, C07, C08, C09, C10
- Not evaluated (file missing/changed, label TBD, or excluded): 2 — B-08, B-20

### Coverage of the 50-case plan

| Category | Description | Planned cases | Images evaluated |
|---|---|---|---|
| C01 | Original smartphone photo, copied as a file from the phone | 1 | 1 |
| C02 | Text-to-image generated with ChatGPT | 2 | 2 |
| C03 | Text-to-image generated with Google Gemini | 1 | 1 |
| X00 | Extra source image used to create derivatives | 21 | 19 |

| Category | Description | Ground truth | Images |
|---|---|---|---|
| C01 | Original smartphone photo, copied as a file from the phone | REAL | 1 |
| C02 | Text-to-image generated with ChatGPT | AI_GENERATED | 2 |
| C03 | Text-to-image generated with Google Gemini | AI_GENERATED | 1 |
| X00 | Extra source image used to create derivatives | AI_EDITED | 1 |
| X00 | Extra source image used to create derivatives | AI_GENERATED | 4 |
| X00 | Extra source image used to create derivatives | MANUALLY_EDITED | 1 |
| X00 | Extra source image used to create derivatives | REAL | 13 |

## Overall outcome

| Correct | Incorrect | Inconclusive | Accuracy (decided) | Accuracy (inconclusive = wrong) | Source-weighted accuracy |
|---|---|---|---|---|---|
| 16 | 4 | 3 | 0.8 | 0.696 | 0.69 |

Correctness rules: REAL → no-AI/authentic; AI_GENERATED → Likely AI; AI_EDITED and MIXED → Likely AI or Potential manipulation; MANUALLY_EDITED → Potential manipulation (a 'Likely AI' verdict on a Photoshop-only edit is counted as a false AI accusation).

## Confusion matrix

| Ground truth \ Predicted | Likely AI-generated | Likely authentic | No AI detected | Potential manipulation | Inconclusive | Total |
|---|---|---|---|---|---|---|
| REAL | 0 | 1 | 10 | 0 | 3 | 14 |
| AI_GENERATED | 5 | 0 | 2 | 0 | 0 | 7 |
| AI_EDITED | 0 | 0 | 1 | 0 | 0 | 1 |
| MANUALLY_EDITED | 0 | 0 | 1 | 0 | 0 | 1 |

## AI-involvement detection (binary)

positive = AI_GENERATED, AI_EDITED, MIXED; negative = REAL, MANUALLY_EDITED; predicted positive = 'Likely AI-generated'; 'Inconclusive' = abstention

| TP | FP | TN | FN | Abstained |
|---|---|---|---|---|
| 5 | 0 | 12 | 3 | 3 |

| Metric | Value | 95% Wilson CI |
|---|---|---|
| Precision | 1.0 | [0.566, 1] |
| Recall (decided) | 0.625 | [0.306, 0.863] |
| Recall (abstention = miss) | 0.625 |  |
| F1 (decided) | 0.769 |  |
| False-positive rate | 0.0 | [0, 0.243] |
| Coverage | 0.87 |  |

## Editing detection

edited = MANUALLY_EDITED, AI_EDITED, MIXED or secondary MANUALLY_EDITED; flagged = 'Potential manipulation'

| Edited images | Flagged | Detection rate | 95% CI | Unedited images | False alarms | False-alarm rate |
|---|---|---|---|---|---|---|
| 2 | 0 | 0.0 | [0, 0.658] | 21 | 0 | 0.0 |

## False positives — authentic or manually edited images called AI

_None._

## False negatives — AI-involved images called not-AI

| Image | Cat. | Ground truth | Predicted | AI indicator | View agreement | Metadata | Transformation |
|---|---|---|---|---|---|---|---|
| B-02 | X00 | AI_GENERATED | No AI detected | 0.0385 | 0.857 | no camera EXIF; JPEG q~92 | pasted into chat (re-encoded by the chat client, metadata stripped) |
| B-06 | X00 | AI_EDITED | No AI detected | 0.0124 | 1.0 | no camera EXIF; JPEG q~87 | pasted into chat (re-encoded by the chat client, metadata stripped) |
| B-18 | X00 | AI_GENERATED | No AI detected | 0.0633 | 0.857 | no camera EXIF; WEBP | pasted into chat (re-encoded by the chat client, metadata stripped) |

## Missed manual edits (Photoshop edits reported as clean)

| Image | Cat. | Ground truth | Predicted | AI indicator | View agreement | Metadata | Transformation |
|---|---|---|---|---|---|---|---|
| B-07 | X00 | MANUALLY_EDITED | No AI detected | 0.0066 | 1.0 | no camera EXIF; JPEG q~72 | pasted into chat (re-encoded by the chat client, metadata stripped) |

## False edit alarms (clean images reported as manipulated)

_None._

## Breakdown by test category

| Category | N | Correct | Incorrect | Inconclusive | Acc. (decided) | Acc. (strict) |
|---|---|---|---|---|---|---|
| C01 | 1 | 1 | 0 | 0 | 1.0 | 1.0 |
| C02 | 2 | 2 | 0 | 0 | 1.0 | 1.0 |
| C03 | 1 | 1 | 0 | 0 | 1.0 | 1.0 |
| X00 | 19 | 12 | 4 | 3 | 0.75 | 0.632 |

## Breakdown by source tool

| Origin tool | N | Correct | Incorrect | Inconclusive | Acc. (decided) | Acc. (strict) |
|---|---|---|---|---|---|---|
| ChatGPT | 3 | 2 | 1 | 0 | 0.667 | 0.667 |
| Gemini | 3 | 3 | 0 | 0 | 1.0 | 1.0 |
| iPhone 11 Pro | 1 | 1 | 0 | 0 | 1.0 | 1.0 |
| internet landscape | 2 | 1 | 0 | 1 | 1.0 | 0.5 |
| internet landscape (AVIF) | 1 | 1 | 0 | 0 | 1.0 | 1.0 |
| internet news photo | 1 | 1 | 0 | 0 | 1.0 | 1.0 |
| internet photo | 1 | 0 | 0 | 1 |  | 0.0 |
| internet thumbnail | 1 | 0 | 1 | 0 | 0.0 | 0.0 |
| phone (user) | 5 | 5 | 0 | 0 | 1.0 | 1.0 |
| phone + ChatGPT 'improve quality' | 1 | 0 | 1 | 0 | 0.0 | 0.0 |
| phone via Instagram | 1 | 1 | 0 | 0 | 1.0 | 1.0 |
| phone via WhatsApp (user) | 1 | 0 | 0 | 1 |  | 0.0 |
| unknown AI tool | 1 | 0 | 1 | 0 | 0.0 | 0.0 |
| webcam (user) | 1 | 1 | 0 | 0 | 1.0 | 1.0 |

## Breakdown by transformation tool

| Transformation tool | N | Correct | Incorrect | Inconclusive | Acc. (decided) | Acc. (strict) |
|---|---|---|---|---|---|---|
| chat client paste | 18 | 11 | 4 | 3 | 0.733 | 0.611 |
| — | 5 | 5 | 0 | 0 | 1.0 | 1.0 |

## Processing time

Median 2590.7 ms, max 4317.7 ms.

## Models

| Model | License | Device | Loaded |
|---|---|---|---|
| haywoodsloan/ai-image-detector-deploy | Apache-2.0 | cuda | yes |
| prithivMLmods/Deep-Fake-Detector-v2-Model | Apache-2.0 | cuda | yes |

## Caveats

- Small samples: with 5 images per category one error moves a rate by 20 points; read the confidence intervals.
- Derived images share content with their original; the source-weighted accuracy counts each source once.
- `backend/eval_images` was used to choose the detector and thresholds; this test set is checked to share no files with it.
