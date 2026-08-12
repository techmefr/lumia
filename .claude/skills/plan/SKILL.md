---
name: plan
description: Use when the architecture is set, before writing tests or code, break the feature into atomic testable tasks.
---

# plan

Step 4 of the pipeline (`WORKFLOW.md`). Turn the target architecture into deliverable
increments.

## When
After `archi`, before `tdd`.

## Steps
1. Break into **atomic** increments: each one testable and deliverable independently.
2. Order by dependency (whatever unblocks the rest comes first).
3. Record **one tracked item per increment**, wherever the task's trail lives (a todo list, the ticket, a
   local orchestrator if there is one). The tracking must exist; the tool is not prescribed.

## Output / checkpoint
`plan_done` + one tracked item per increment, in dependency order.

## Guardrails
No automatic execution of the whole plan (**no `/build auto`**: see `WORKFLOW.md`, auto-mode
was removed on purpose). The dev validates and moves forward step by step.

## Origin
Native / a market generalist dev skill catalogue (planning-and-task-breakdown), rewritten our
way.
