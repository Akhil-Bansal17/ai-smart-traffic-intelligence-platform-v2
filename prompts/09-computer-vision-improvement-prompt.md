# 09 — Computer Vision Improvement Prompt

**Use when:** improving detection, tracking, or counting accuracy.

## Role
CV engineer diagnosing pipeline weaknesses with evidence, not intuition.

## Context to Read
`backend/app/services/cv/*`, current confidence/threshold config, any evaluation videos or logged detection output.

## Objective
Improve measurable CV pipeline quality: detection accuracy, tracking stability, counting correctness, lane assignment correctness, occlusion handling, false positive/negative rate, and processing performance.

## Workflow
1. Establish current behavior on a real test video (not synthetic assumptions) — note actual false positives/negatives observed.
2. Form a specific hypothesis for one improvement (e.g., "raising confidence threshold from 0.3→0.45 should reduce false positives on small/occluded vehicles").
3. Implement that one change.
4. Re-test on the same video and compare directly.
5. Keep the change only if it's a measured improvement; otherwise revert and record what was learned.

## Expected Output
Before/after observations on the same test input, and the resulting code change (or explicit rollback).

## Restrictions
Never claim an accuracy/FPS improvement without a before/after comparison actually run.
