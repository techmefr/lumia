---
name: handoff
description: Use when a task spills over a session and the context has to be passed cleanly to a fresh session/agent, compacts the state into a handover document that references the artefacts already written (plan, ADR, ticket, commit, diff) by path/URL rather than duplicating their content.
---

# handoff

Cross-cutting step, at the boundary between two sessions on the same task: complements
the one-task-per-worktree rule: the worktree stays open, but the context of the session
that's ending has to survive cleanly into the next one.

## When
As soon as a session is coming to an end (context limit, end of day, change of who picks it up)
without the task being finished: never as a replacement for a plain end-of-task summary on a
completed task.

## Steps

1. **Write a handover document** (a dedicated temporary file, not mixed into the code) containing:
   where we are, what's left to do, what was decided and why, what's blocking if there is a
   blocker.
2. **Reference, never duplicate**: point at the artefacts already written by their exact path/URL
   (plan, ADR, Jira ticket, commit, diff in progress) rather than copying their content into the
   handover document: a handoff that duplicates inflates the next session's context for nothing.
3. **Suggest the relevant skills** for what follows (e.g. "resume at `tdd`, the `plan` is already
   done and referenced here"): the next session knows where to restart without having to
   rediscover the state on its own.
4. The next session reads the handover document first, before any other exploration: it saves the
   re-contextualisation time.

## Output / checkpoint
A handover document exists, cites every artefact by its exact path/URL (no duplicated content),
and explicitly names the next step/skill to resume at.

## Guardrails
Never duplicate content already written elsewhere: the whole principle of this block is
referencing, not copying. A handoff that ends up longer than the artefacts it references has
missed its goal.

## Origin
Rewrite of the `handoff` skill from a recognised market skill author: the rule "never duplicate,
reference by path" is taken as-is, rewritten to the mentis template and explicitly linked to
the one-task-per-worktree rule already in place in house.
