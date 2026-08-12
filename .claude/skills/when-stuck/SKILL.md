---
name: when-stuck
description: Use when the work has stalled and more effort in the same direction isn't helping, pick the technique that matches the kind of stuck you're in rather than pushing harder. Distinct from debug (a wrong behaviour with a findable cause): this is for when the approach itself is the problem.
---

# when-stuck

Cross-cutting (`WORKFLOW.md` §2). `debug` handles a bug: something behaves wrongly and there's a cause
to trace. This block handles the other kind of stuck, where nothing is failing exactly, the approach
just isn't working, and the instinct is to try the same thing with more determination.

The first move is diagnosis: **which kind of stuck is this**. Applying the wrong technique is how you
spend an afternoon being creative about a problem that needed a measurement.

| Symptom | Technique |
|---|---|
| Special cases multiplying, several near-identical implementations | §1 unify, or delete |
| "It has to be done this way" and nobody can say why | §2 invert the assumptions |
| Works here, unclear whether it survives production | §3 push the scale to the extremes |
| The same problem keeps reappearing in different places | §4 name the pattern once |
| Something behaves wrongly, with a traceable cause | not here → `debug` |
| Blocked on information only a human has | not a technique → ask |

## When
As soon as the same approach has been retried without progress — a spec that won't settle, a design
decision that keeps reversing, a bug whose cause moves every time you look, a task that has been "almost
done" for hours. **Not** for a wrong behaviour with a findable cause: that is `debug`.

## Steps

### 1. Unify, or delete: the simplification cascade
When you have four things doing almost the same job:
1. **Inventory the variations** honestly, all of them.
2. **Find the sentence that unifies them** — the "if this is true, we don't need X, Y and Z". That
   sentence is the whole technique; without it you're just planning a refactor.
3. **Check every existing case fits** the unified model, including the awkward one. The awkward one is
   usually why there were four.
4. **Count the lines it deletes against the lines it adds.** A cascade that unifies four things into
   one abstraction and removes nothing is over-abstraction wearing the costume of simplification.
   That's the `over-engineering-review` test, and it applies here in full: if the complexity moved
   rather than disappeared, don't do it.

### 2. Invert the assumptions
When you feel boxed into the only possible approach:
1. **List what must be true** for the current approach to be the right one. Write the assumptions
   down; unwritten ones don't get questioned.
2. **State the opposite of each**, even when it sounds absurd.
3. **Follow the implications**: what would change if the opposite held?
4. **Keep the inversions that survive contact with reality.** Most won't. The one that does is usually
   the thing you couldn't see: "faster is always better" inverts into a deliberate debounce, which is
   both slower per keystroke and better overall.

### 3. Push the scale to the extremes
When "will this hold?" is vague:
1. **Pick the dimension** that worries you: volume, users, duration, failure rate, latency.
2. **Run it mentally at a thousand times more, and a thousand times less.** Not double, not half:
   extremes are what expose the assumption.
3. **Name what breaks first.** An in-memory cache that's fine for hours is unbounded growth over
   years. A synchronous call that's fine locally is unusable across a continent. An error handler
   that's fine for occasional failures collapses at a constant rate.
4. This converts "will it scale" into a specific failure you can decide to accept or prevent.

### 4. Name the pattern once
When the same shape keeps reappearing:
1. **Require three occurrences** in genuinely different places before generalising. Two is a
   coincidence, and generalising from two is how a bad abstraction gets born.
2. **Strip the domain vocabulary** and state what's actually happening underneath.
3. **List what varies** between the occurrences: that's what the general form has to parameterise, and
   if the list is long, they weren't the same problem.
4. Then apply §1's line count before building anything.

## Output / checkpoint
No checkpoint of its own: it feeds back into whichever step was stuck. What it owes is a decision —
the technique applied, what it revealed, and what changes — not a page of exploration.

## Guardrails
- **Timebox it.** This block exists to break a stall, not to become the afternoon. If no technique has
  produced a decision, that's the signal to ask a human, not to try a fifth angle.
- **Don't reach for a technique when the blocker is information.** If the answer lives in someone's
  head or in the business's rules, no amount of inversion produces it. Ask.
- **A technique that produces an insight but no change produced nothing.** Interesting is not the bar.
- §1 and §4 both propose generalising, and both are net-negative if they add more than they remove.
  The line count isn't a formality, it's the check that keeps this block from becoming a licence to
  abstract.

## Origin
Rewrite of the `problem-solving/` category from a market skills repository (the companion of the
upstream this framework responds to): `when-stuck` as a dispatch, plus `simplification-cascades`,
`inversion-exercise`, `scale-game` and `meta-pattern-recognition`.

Two deliberate departures. **Merged into one block instead of six**: these are techniques you reach
for rarely, and six separate files is six files nobody opens — the symptom→technique table at the top
is how the thing actually gets used, so it's the block, not an index pointing elsewhere.
**`collision-zone-thinking` was not taken**: forcing two unrelated domains together (code as biology)
generates metaphors reliably and decisions rarely, and this framework already errs toward too much
material rather than too little. Also added: the three-occurrence threshold before generalising, and
the requirement that §1 and §4 pass the `over-engineering-review` line count — the source presents
unification as straightforwardly good, which collides with our standing preference for less logic to
maintain.
