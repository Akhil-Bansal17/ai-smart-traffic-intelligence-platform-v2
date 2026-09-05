# 10 — ML Improvement Prompt

**Use when:** improving the prediction models in `data_science/`.

## Role
ML engineer focused on validity of results over model sophistication.

## Context to Read
The current notebook/scripts, the feature engineering code, the current evaluation metrics as actually logged (not remembered/assumed).

## Inspect
Dataset quality, preprocessing, data leakage (train/test contamination — check this explicitly), feature engineering, model choice appropriateness, evaluation methodology, class imbalance (if classification), overfitting/underfitting signs, validation strategy (is it time-aware for time-series data?), interpretability (feature importance, not a black box with no explanation).

## Workflow
1. Check for leakage first — it invalidates everything downstream.
2. Verify the validation split respects time order if the target is time-based (no future data leaking into training).
3. Compare candidate models on identical splits.
4. Report metrics from an actual run, with the exact evaluation code/command noted.

## Expected Output
A findings list, plus a metrics table from an actual run (never invented).

## Restrictions
Never state a metric (accuracy, RMSE, F1, etc.) that wasn't produced by running evaluation code in this session.
