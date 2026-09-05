# 06 — Code Review Prompt

**Use when:** reviewing a completed feature or phase before merging/committing it as done.

## Role
Independent reviewer — assume the author (even if it was you, earlier) may have missed something.

## Context to Read
The changed files, the relevant section of `ARCHITECTURE.md`, and any tests written for the change.

## Objective
Find real issues before they become technical debt or portfolio embarrassments.

## Inspect
Architecture fit, correctness, maintainability, security, performance, test coverage, naming, duplication, error handling.

## Workflow
1. Read the diff/feature end to end before commenting.
2. List findings, each tagged with severity (Critical/High/Medium/Low).
3. For each: what's wrong, why it matters, suggested fix.
4. Note what's genuinely good too — review isn't only a defect list.

## Expected Output
A findings list ranked by severity, plus a short overall verdict (ready / ready with fixes / not ready).

## Verification
Point to the specific file/line for every finding — no vague "this could be cleaner" without a location.

## Restrictions
Don't rewrite the code yourself in a review pass unless asked — flag issues first.
