# 11 — Data Science / EDA Prompt

**Use when:** exploring traffic data before feature engineering or modeling.

## Role
Data scientist doing honest exploratory analysis.

## Context to Read
Raw data source(s) (`traffic_metrics`, `detections` tables or exported CSVs), `data_science/notebooks/`.

## Objective
Understand the data before modeling it: distributions, missingness, outliers, correlations, temporal patterns (daily/weekly seasonality in traffic is likely — check for it, don't assume it).

## Workflow
1. Load and profile the data (shape, dtypes, missing values, obvious data-entry errors).
2. Visualize distributions and time patterns.
3. Note anything that will affect feature engineering or modeling choices (e.g., sparse lanes, sensor gaps).
4. Summarize findings in the notebook with markdown commentary, not just code and plots.

## Expected Output
A documented EDA notebook plus a short written summary of what it implies for modeling.

## Restrictions
Don't jump to feature engineering/modeling in the same pass without first documenting what EDA found.
