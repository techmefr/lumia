---
name: dispatch-parallel
description: Use when a task splits into independent sub-parts (several stacks to review, several files to migrate, several leads to explore), launch subagents in parallel on disjoint scopes rather than a single sequential agent.
---

# dispatch-parallel

Cross-cutting block (not a numbered pipeline step): applies as soon as a piece of work naturally
decomposes into sub-tasks that don't step on each other.

## When
- Several stacks/repos to handle in the same pass (e.g. `elrond` delegating to
  `aragorn`/`gimli`/`legolas` in parallel on disjoint MRs).
- Several independent files/modules to migrate, audit or document.
- Several research leads to explore before deciding (judge panel, several candidate
  implementations).
- Does **not** apply if the sub-tasks share common mutable state (the same file edited by two
  agents at once): in that case, sequential.

## Steps
1. **Split into disjoint scopes**: each subagent gets a clear scope that overlaps no other
   (different files, or the same file read-only for all but one).
2. **Isolate by worktree** if the subagents write code (see `merge-worktree`): never two agents
   writing in the same working directory at the same time.
3. **Launch in a single message** all the independent agents (several tool calls in the same
   turn) rather than in series: the gain only exists if the waiting is genuinely concurrent.
4. **Aggregate** the results once they've all come back: don't start synthesising before you have
   everything, unless the pipeline is built as a continuous pipeline (a result moves to the next
   step as soon as it's ready, without waiting for the others).
5. Every subagent produces its own trace (see the single template, pillar 7): no merged report
   that hides which agent said what.

## Output / checkpoint
Every dispatched subagent has come back (or been explicitly abandoned with the reason noted), and
the aggregation cites which result comes from which agent: never an anonymous synthesis.

## Guardrails
- Never two agents with Write/Edit on the same file simultaneously.
- One agent failing doesn't cancel the others: isolate the failure, don't relaunch the whole
  batch.
- Don't dispatch for the sake of dispatching: a single sub-task doesn't justify this mechanism, it
  only pays off if the parallelism saves real time.

## Origin
Rewrite of the two ideas `dispatching-parallel-agents` and `subagent-driven-development` from a
market skill/agent framework, merged here because in our usage they overlap: dispatching in
parallel and delegating to specialised subagents are the same decision here (`elrond` →
`aragorn`/`gimli`/`legolas`/`boromir`/`theoden`/`frodo` is the lived production example).
