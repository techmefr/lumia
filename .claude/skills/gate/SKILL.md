---
name: gate
description: Use when the code is written, before the review, mechanical lock: declaring a criterion "passing" without evidence is forbidden, and a clean-context evaluator decides.
---

# gate

Step 7 of the pipeline (`WORKFLOW.md`). **The number one reinforcement from the scouting.**
Turns "tests are green" from a declarative wish into a **proven fact**. "Done" becomes
structural, not a claim.

## When
After `code` (implementation done), before `review`.

## Steps
1. For every `{ passes: false }` line in `test-results.json`, **produce evidence**: test
   output, `verify-flow` screenshot, or a log; then **read** it (`Read`).
2. The native `PreToolUse` hook **refuses** to write `passes: true` until the matching evidence
   has been read. You cannot declare yourself passing without observing. The scripts and the
   per-repo wiring are in [`hooks/`](../../hooks/README.md); "exists" isn't enough, the evidence
   has to appear in the read log.
3. Run the **clean-context evaluator**: a subagent **with no Write/Edit**, which didn't watch
   the build, examines the diff + the evidence and returns `PASS` or `NEEDS_WORK` + findings.
4. `NEEDS_WORK` → the findings become the prompt for the next `code` pass, driven by native
   `/goal`: the exit condition is exactly the evaluator's verdict (`PASS`), so this is a goal-based
   loop, not a manual relaunch. `/goal` re-invokes step 1-3 until `PASS` or the attempt cap.

## Output / checkpoint
`verified`: every line `passes: true`, each backed by evidence that was read, evaluator `PASS`.

## Guardrails
The agent **cannot validate itself**: validation comes from the hook (evidence) + the
evaluator (clean context). Stays within native Claude Code (hooks + subagent + `/goal`), no
homemade layer — we invoke the native loop, we don't reimplement it.

## Origin
Market long-running agent patterns (default-FAIL hook + fresh-context evaluator), rewritten
our way. The iteration itself is native `/goal` (Claude Code goal-based loops), not a block.
