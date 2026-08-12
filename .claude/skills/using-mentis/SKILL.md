---
name: using-mentis
description: Use when starting any task in a project that has these blocks installed, to establish the pipeline (start-feature → brainstorm → spec → archi → plan → tdd → code → gate → review → simplify → ship → finish) and the discipline of invoking the block that applies instead of improvising.
---

# using-mentis

Entry point of the method layer, read at the start of every task. The full step table, the two backward
loops and the guarantees are in `WORKFLOW.md`; this block is the *habit*, not the reference.

## When
At the start of any task. Also mid-task, when you notice you're improvising a step a block already owns.

## Steps

### 1. Name the block before acting
1. **Before any action** — including a clarifying question or exploring the repo — identify the block that
   applies and invoke it. Say which one and for what, then follow it.
2. **If it has a checklist, one todo per item.** A checklist read but not tracked is a checklist half done.
3. **"I already know how to do this" is not "I followed the block."** The block exists because the memory
   of it is worse than the text of it.
4. **No block fits?** That's either out of scope, or a gap to record — not a licence to invent a step
   silently (`skills/writing-skills`).

### 2. The order, and where each step ends
| # | Block | Ends at |
|---|---|---|
| 0 | `start-feature` | isolated worktree on a fresh branch |
| 1 | `brainstorm` | intent stated, options weighed |
| 2 | `spec` | scope and out-of-scope locked, criteria verifiable → `spec_done` |
| 3 | `archi` (+ `domain-modeling`, `api-design`, `documentation-adr`, `design-patterns`) | reuse-vs-create decided, no duplicate → `arch_done` |
| 4 | `plan` | atomic increments in dependency order → `plan_done` |
| 5 | `tdd` (+ `testing-anti-patterns`) | tests first, failing for the right reason → `tests_written` |
| 6 | `code` + the conventions block for the stack | increments built, `debug` in support → `build_done` |
| 7 | `gate` | evidence produced **and read**, fresh-context verdict → `verified` |
| 8 | `review` (+ `qa-exploratory-testing`) | findings triaged, verified, posted |
| 9 | `simplify` (+ `over-engineering-review`) | net deletion where deletion was possible |
| 10 | `ship` | draft MR pushed → `awaiting_human`. **The agent stops here.** |
| 11 | `finish` | worktree removed, base branch updated |

A reported bug enters at `bug-triage` before `debug`. Not every task needs every step — a one-line fix
gets no brainstorm — but the **direction** is not optional: never review before the gate, never gate work
you're still writing.

### 3. State and orchestration
1. **Each step records what was proven**, not what was attempted (`WORKFLOW.md` §5), so a dead session
   resumes without re-deriving settled decisions. `handoff` covers the pass between two sessions.
2. **Where a local orchestrator exists** (task registry, port allocation, dashboard), let it hold the
   state and let the blocks decide the method. **Method ≠ state.**
3. **But no block requires it.** Every block must work with plain git and no extra tooling — that's rule B
   applied to ourselves, and `start-feature` had to be corrected for breaking it.

## Output / checkpoint
The pipeline entered at the right step, each step's checkpoint recorded as it clears, and the task stopped
at the draft MR for a human.

## Guardrails
- **The approvals and the merge are outside agent scope.** Stop at the draft MR and hand back.
- **Never skip the gate because the change looks small**, and never let the producer be its own judge.
- Blocked and repeating yourself? Escalate rather than loop — three failed hypotheses is the ceiling
  (`skills/debug` §4, `skills/when-stuck`).
- Never invent a step that a block already owns, and never fork a block's rule locally: fix the block.
- Business-layer blocks (`business/`) sit alongside this pipeline and **gate nothing** — see
  `business/README.md`.

## Origin
Internal. The "announce the block, then follow it" discipline is taken from the framework this repo
responds to, where it's the entry-point rule; the step table is ours and mirrors `WORKFLOW.md` §2 rather
than restating it. Rewritten 2026-08-06 to remove a hard dependency on a local orchestrator's MCP tools,
which had made the entry point itself undistributable.
