---
name: ship
description: Use when everything is green and simplified, push the branch and open the MR as a draft; the agent stops here.
---

# ship

Step 10 of the pipeline (`WORKFLOW.md`). The **agent/human boundary**: we prepare, the human
decides.

## When
After `simplify` (`simplified`), GATE tests green.

## Steps
1. Check one last time: GATE `verified`, suite green, checkpoints up to date.
2. Push the branch.
3. Open the **MR as a draft** (author dev + 2 colleagues), clear description (status +
   message).
4. Mark `mr_draft_pushed` / `status: awaiting_human`.

## Output / checkpoint
`mr_draft_pushed`, `status: awaiting_human`.

## Guardrails
**The agent stops here.** The 2 human approvals and the merge are outside agent scope. Never
merge automatically. Commit/MR: conventional commits, lowercase description.

## Origin
Internal (`/SHIP` sequence, `gandalf` final gate), rewritten our way.
