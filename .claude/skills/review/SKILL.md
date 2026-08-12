---
name: review
description: Use when the GATE is green, before simplification, review along two parallel axes (Standards + Spec) then a pass by the house agents.
---

# review

Step 8 of the pipeline (`WORKFLOW.md`). Two independent viewpoints that don't pollute each
other.

## When
After `gate` (`verified`), before `simplify`.

## Steps
0. **Get the diff in.** `references/review-transports.md` decides how: locally
   (`bin/prefetch_local.py`, git only — the default), from a CI checkout, or from a forge merge request. The
   review below is identical in all three; only the way in, and what happens to the findings, differ.
1. Run **two subagents in parallel** (separate contexts, no cross-pollution):
   - **Standards axis**: the stack's conventions + code smells (reuse, simplification, duplicated
     CSS), **then the cross-cutting sweep of `references/mr-review-plumbing.md`'s companion,
     `references/review-axes.md`** — accessibility, trust boundary, tests owed, cost on a hot path,
     diagnosability, contract, deletion, user-visible words. Each axis has an entry condition, so a
     diff that doesn't meet it produces nothing on that axis.
   - **Spec axis**: is the diff **faithful to the ticket / the spec**? (which the native
     `/code-review` doesn't cover). Clean skip if there's no spec.
2. Aggregate both side by side.
3. A pass by the **per-stack reviewer** in the dev's usual style: `elrond` to route, or
   `aragorn`/`gimli`/`legolas`/`boromir`/`theoden`/`frodo` directly if the stack is known.
4. **Triage before posting anything.** The findings from steps 1-3 are raw coverage, not a review:
   verify each one against the real code, drop what would only start a pointless argument, rank
   bugs above nits, and reword each surviving point short and sourced. A wrong or unsourced
   finding costs more credibility than the bug it claimed to catch.
5. For depth: native `/code-review` + `/security-review` (gandalf as the final gate).

## Output / checkpoint
`reviewed`.

## Guardrails
The two axes stay **independent** (no shared context). We invoke the native tooling, we don't
reimplement it. Plain comments, no emojis/arrows, lowercase at the start of a sentence.

## Origin
A recognised market skill author (non-polluting two-axis code review) + the house agents + native,
rewritten. Step 4 (triage before posting) is the generic form of a mechanism that proved itself on
an agent kept private: the agent was calibrated on one named person's habits, which doesn't belong
in a shared framework, but the discipline it encoded holds for any reviewer.
