# 14 — Database Audit Prompt

**Use when:** reviewing schema design, migrations, or query performance.

## Role
Database-focused engineer.

## Context to Read
`ARCHITECTURE.md` §8, actual models/migrations, any slow-query logs or `EXPLAIN` output available.

## Inspect
Schema correctness vs. actual usage patterns, missing indexes, migration consistency with model definitions, retention policy for high-volume tables (`detections`), normalization vs. practical query needs.

## Workflow
1. Compare the schema as documented against the schema as actually migrated — flag drift.
2. Check indexes against the actual query patterns used by the API.
3. Confirm the retention/cleanup policy for `detections` is implemented, not just documented.

## Expected Output
Findings list with concrete migration/index recommendations.

## Restrictions
Don't recommend an index without pointing to the query pattern that needs it.
