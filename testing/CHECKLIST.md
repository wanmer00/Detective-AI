# Detective AI — Test Execution Checklist

Tick each box when done. Run all commands from `backend/`. See `TEST_PLAN.md` for label rules.

## 0. Before collecting
- [ ] Detector, thresholds and rules are frozen; note the date: ________
- [ ] Decide who photographs whom; get consent from anyone recognisable
- [ ] Do **not** take test images from `backend/eval_images`

## 1. Sources (originals)
- [ ] C01 — 5 phone photos copied as files from the gallery (`--category C01 --origin camera --device ...`)
- [ ] X00 — extra phone photos to use as bases for edits (`--category X00 --label REAL --origin camera`), aim for 10+
- [ ] C02 — 5 ChatGPT images, original download, prompt recorded (`--category C02 --origin-tool ChatGPT`)
- [ ] C03 — 5 Gemini images, original download, prompt recorded (`--category C03 --origin-tool Gemini`)
- [ ] X00 — extra AI images as bases for C04/C09 (`--category X00 --label AI_GENERATED`), optional

## 2. Derived images (each needs `--original-id`)
- [ ] C04 — 5 AI images + non-generative Photoshop edits; list every step in `--params`
- [ ] C05 — 5 real photos + non-generative Photoshop edits (clone/heal/colour/paste real photo)
- [ ] C06 — 5 real photos + generative edits (Generative Fill / inpainting / object replacement); prompt in `--params`
- [ ] C07 — 3 real + 2 AI sent **as photos** via Telegram / WhatsApp and saved on the receiving device; app + version in `--transformation-tool`
- [ ] C08 — 5 screenshots (real and AI); device in `--transformation-tool`
- [ ] C09 — 5 conversions of AI images (PNG→JPEG, WEBP, resize, JPEG q60); record tool + settings in the manifest
- [ ] C10 — 5 mixed composites; describe which parts are AI in `--notes`
- [ ] A06 — the ChatGPT "improve quality" case: phone original in C01/X00, enhanced result in A06
- [ ] Optional: A01 upscaling · A02 AI filters · A03 background · A04 screen re-photo · A05 multi-compression

## 3. Before the run
- [ ] Open `manifest.csv`: every row has ground truth, tool, and (for derived) `original_image_id`
- [ ] At least 5 images per category C01–C10 and 30+ independent sources (`source_group_id`)
- [ ] No ground truth was changed after seeing any prediction

## 4. Run
- [ ] `.venv\Scripts\python scripts\run_test_suite.py`
- [ ] Validation passed (IDs, links, hashes, no overlap with eval_images)
- [ ] Note the output folder: `testing/results/run_________________`

## 5. After the run
- [ ] Read `report.md`: confusion matrix, precision/recall/F1 with confidence intervals
- [ ] Review every false positive (real or Photoshop-only image called AI) — note the likely cause
- [ ] Review every false negative (AI-involved image called not-AI) — note the likely cause
- [ ] Review missed edits and false edit alarms
- [ ] Copy the key numbers into the presentation **with sample sizes and intervals**
- [ ] If any rule/threshold is changed afterwards: re-run and keep both reports
