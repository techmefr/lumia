---
name: choose-model
description: Use when writing a new agent, or launching a one-off task, and the Claude model has to be decided, Haiku for mechanical/repetitive low-stakes tasks, Sonnet by default for build and review, Opus for a gate or a judge whose verdict is hard to walk back (blocks a merge, a decision).
---

# choose-model

Cross-cutting block (not a numbered pipeline step): applies every time an agent is created or a
one-off task is launched without a model already imposed.

## When
- While writing a new agent (`model:` frontmatter to fill in).
- While launching a one-off task where the model isn't already set by an existing agent.
- When in doubt whether an existing agent is on the right model (over- or under-sized).

## Steps

1. **Characterise the task**, not the agent's role:
   - Is it mechanical/repetitive (extraction, formatting, short summary, simple
     classification)? → **Haiku**.
   - Is it building work or normal reading (writing code, reviewing a diff, applying documented
     conventions)? → **Sonnet**, the default.
   - Is the verdict hard to walk back once taken (blocks a merge, decides between two
     architectures, judges with a fresh context and no immediate second chance)? → **Opus**.
2. **Check the cost of being wrong**, not just the apparent complexity: a task that looks simple
   but where an error is expensive to recover from (e.g. a gate that lets a bug through to
   production) moves up a tier rather than staying at the "perceived complexity" level.
3. **Never over-size out of reflex.** Opus everywhere is expensive and improves nothing on a
   mechanical task: over-sizing is a choice error too, not just under-sizing.
4. **Document the choice** in the agent's frontmatter (`model: sonnet` for instance): never left
   implicit, so that a later re-read can challenge the choice on explicit criteria.

## Output / checkpoint
The agent frontmatter's `model:` field is filled in, with a choice justifiable in one sentence
against the grid above. For a one-off task with no dedicated agent, the model is chosen before
launching, not changed halfway through unless there's a strong signal (timeout, repeated
failure).

## Guardrails
- No rigid rule by agent name: an already "known" agent can change tier if the real nature of its
  work has changed.
- When in doubt between two tiers, take the lower one and move up only if a concrete failure
  justifies it: not the other way round.

## Origin
Internal decision grid: characterisation by the nature of the task
(mechanical/building/hard-to-undo verdict) and by the cost of being wrong, not by perceived
complexity. No specific external source retained: several market model-routing frameworks exist,
but none was judged close enough to our stack/agent reality to be rewritten as-is; the grid above
is a synthesis of our own.
