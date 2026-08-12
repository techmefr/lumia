---
name: spec
description: Use when locking down the scope of a feature before the plan, clarification interview, explicit scope + out-of-scope, CONTEXT.md and ADR.
---

# spec

Step 2 of the pipeline (`WORKFLOW.md`). Lock down *what* we're building, with a shared
vocabulary and traced decisions.

## When
After `brainstorm`, before `/PLAN`. Or as soon as the scope / acceptance criteria are unclear.

## Steps
1. **Interview** the dev: one targeted question per ambiguity, until the scope is sharp.
2. Write **`CONTEXT.md`**: the shared vocabulary of the feature (terms, entities, business
   rules).
3. List the explicit **acceptance criteria** (they become the contract for `tdd`).
4. List the explicit **out-of-scope**.
5. Write an **ADR** for every structural decision (choice + alternatives ruled out + why).

## Output / checkpoint
`spec_done` + `CONTEXT.md` + ADR(s).

## Guardrails
No code. If the scope is still unclear after the interview, `escalate` rather than guess.

## Origin
A recognised market skill author (grill-with-docs → CONTEXT.md + ADR) + internal
`spec-clarification`, rewritten.
