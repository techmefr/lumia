---
name: over-engineering-review
description: Use when re-reading a diff or a whole repo looking for one thing only, what can be deleted (dead code, reinvented stdlib, over-abstraction, unrequested anticipation). Complements the diff reviewers/gandalf (which judge correctness and conventions) and the native simplify skill (which applies the fixes): here we only score and list, pure deletion angle.
---

# over-engineering-review

Step `simplify` (9) of the pipeline (`WORKFLOW.md`), or a one-off mode on a diff before merge.
A single question asked of every line in scope: **can this disappear without breaking
anything?** No correctness judgement (that's the diff reviewer), no convention judgement (the
`*-conventions` blocks): only the hunt for what should never have been written.

## When
- Alongside the diff reviewer/`gandalf` on an MR, when a diff looks bigger than the need
  justifies.
- As a one-off audit of a whole repo (not just a diff) when over-engineering debt is suspected.
- As raw material for the native `simplify` skill, which then applies the deletions retained:
  this block fixes nothing itself, it lists and scores.

## Steps

### Diff mode (a change in progress)
Go through only the added/modified lines of the diff. For each candidate found, one finding line
with a tag:

- `to-delete:`, dead code, never called, or duplicated from an existing helper already present
  in the repo (see also [[reuse-existing-components-before-creating]]).
- `stdlib:`, a function/utility reinvented when the language, the framework or an
  already-installed lib does it natively.
- `over-abstraction:`, an interface, wrapper or delegation layer with only one real caller: the
  abstraction is useless until a second use case exists.
- `yagni:`, a feature, option or parameter anticipated for a need nobody asked for today (flag,
  pre-emptive chunking, cache, unused config).
- `to-shrink:`, the same behaviour reachable with appreciably less code (dead branches, cases
  never reached, pointless indirection).

Finding format: `<tag> file:line, what, in one sentence`. No paragraph, no expanded
justification (see [[short-review-checklist-items]]), the dev fixes it or asks.

### Audit mode (whole repo)
Same tag grid, a broad sweep rather than a diff. Priority to the oldest modules or the ones
touched least recently (old git blame = less chance of having been cleaned up already).

## Output / checkpoint
A list of tagged findings, ending with an overall score:
- `net: -N lines possible` if concrete deletions are found, N = a low estimate of lines that can
  be deleted without breaking anything.
- `already lean, nothing to report` if the scope holds no candidate: an audit that finds nothing
  is a valid result, not a failure of the review.

## Guardrails
Never fix anything yourself: this block lists, `simplify` (native skill) or the dev applies.
Don't confuse it with a correctness review: a potential bug spotted along the way is reported
separately (to the diff reviewer/gandalf), not mixed into this list. An `over-abstraction`
candidate requires checking that there really is only one caller (grep before deciding), no
deletion on an assumption.

## Origin
Idea taken from a market deletion-oriented review tool (`ponytail-review`/`ponytail-audit`
skills, deletion angle only, per-category tags, net line score): mechanism and tags rewritten in
the vocabulary of the mentis blocks, no copied text.
