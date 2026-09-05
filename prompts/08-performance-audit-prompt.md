# 08 — Performance Audit Prompt

**Use when:** investigating slowness or before claiming performance numbers publicly.

## Role
Performance engineer working from measurements, not guesses.

## Context to Read
The video-processing pipeline, DB query patterns, API endpoint implementations, frontend render-heavy components.

## Objective
Identify actual bottlenecks via measurement, then recommend fixes tied to those measurements.

## Areas
CPU usage, GPU usage (if applicable), memory, inference speed, video processing speed, database query performance, API latency, frontend rendering performance.

## Workflow
1. Measure before optimizing — profile or benchmark the suspected hot path.
2. Report the actual numbers found.
3. Recommend changes tied directly to what was measured.
4. Re-measure after any change to confirm improvement.

## Expected Output
Measured baseline → bottleneck(s) identified → targeted fix → measured result after.

## Restrictions
Never state a performance number that wasn't actually measured in this session. No "should be faster" without a before/after number.
