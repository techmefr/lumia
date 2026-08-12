---
name: brainstorm
description: Use when a feature starts, before any spec or code, explores the real intent and the options before locking anything down.
---

# brainstorm

Step 1 of the pipeline (`WORKFLOW.md`). Explore the *why* and the possible approaches before
freezing the scope.

## When
Right after `start-feature`, before `/SPEC`. As soon as the real need isn't 100% certain.

## Steps
1. Restate the real need (the problem, not the solution asked for).
2. List 2-3 possible approaches with their trade-offs.
3. Spot the risks and the grey areas.
4. Note a suspected out-of-scope and the open questions for the dev/human.

## Output / checkpoint
No formal checkpoint: a written summary of the intent and the options weighed, kept where the task's trail
lives (`WORKFLOW.md` §5). Prepares `spec` (2).

## Guardrails
No code. Product choices go back to the dev/human, we don't decide alone.

## Origin
Native Claude Code (`brainstorming` skill), rewritten our way.
