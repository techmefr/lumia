---
name: documentation-adr
description: Use when a significant architecture decision that is hard to walk back is taken, separates the ADR (the decision, with context/alternatives/consequences) from inline docs (only the non-obvious why) and from API docs, with a precise ADR template and a never-delete-always-supersede rule.
---

# documentation-adr

Step 3 of the pipeline (`WORKFLOW.md`, after `archi`), for any significant decision that is
expensive to undo: not for documenting every minor choice.

## When
After `archi` (3), as soon as a structural decision is taken (choice of a technology, of a
migration pattern, of a boundary between modules): never for a local, easily reversible choice.

**An ADR is not written unprompted.** A significant decision is *proposed* as an ADR — its six
fields, in the chat reply or the PR description — never *committed as a new file* on your own
initiative. Writing the file is triggered by one of: the user explicitly asks for it; the project
already has an established ADR practice (an existing `docs/adr/`-shaped folder, or a house
convention naming one); or the user accepts the proposal. A repo with a documentation policy that
treats an unsolicited doc file as a defect (`no-project-docs`-shaped: code and commit/PR messages
carry the explanation, not a prose file nobody asked for) is the default case to assume absent a
signal otherwise, not the exception.

## Steps

### 1. Tell the three types of documentation apart
1. **ADR** (Architecture Decision Record): a significant decision, hard to walk back: a dedicated
   file, never mixed into the code.
2. **Inline docs** (a comment in the code): only the non-obvious **why** (hidden constraint,
   workaround, surprising behaviour): never what the code already says (existing rule
   `no-comments-in-blade`: no comment if well-named code is enough).
3. **API docs**: the contract consumed by others (see `api-design`), not the same document as an
   ADR.

### 2. ADR template: six fields, always the same
1. **Status**: proposed / accepted / superseded (never an indefinite "in progress").
2. **Date**: the date of the decision, to place the context in time.
3. **Context**: the situation that made the decision necessary, what won't be obvious any more in
   six months.
4. **Decision**: what was decided, in a sharp formulation.
5. **Alternatives considered**: every option ruled out, with its pros/cons; without that, a future
   reader can't tell whether the alternative was considered or forgotten.
6. **Consequences**: what the decision implies, including the trade-offs accepted.

### 3. Never delete, always supersede
1. An ADR is **never deleted** even if the decision becomes obsolete: a new ADR explicitly
   replaces it (`Status: superseded by ADR-0042`).
2. The decision history stays readable over time: understanding why we changed our mind matters as
   much as the current decision.

### 4. Say when a trade-off is permanent
1. Some decisions don't resolve a tension, they **hold it**: two things that both matter and pull in
   opposite directions (a boundary that costs indirection but keeps two teams independent, duplication
   kept deliberately because merging it would couple two lifecycles).
2. When that's the case, say so in **Consequences**: this tension is deliberate and stays. Otherwise the
   next reader sees only the cost, "simplifies" it, and rediscovers the reason the hard way — usually
   during `simplify`, which is exactly the step that trusts an ADR.
3. This is one sentence, not a section. An ADR that philosophises about tensions is worse than one that
   names the one it's keeping.

## Output / checkpoint
Every significant decision from the `archi` step has its six fields **proposed**, in chat or the PR
description; an ADR **file** exists only where writing one was actually triggered (see `## When`),
and where it does, never a field left empty "to go faster".

## Guardrails
Don't write an ADR for a trivial/reversible choice: reserved for decisions that are expensive to
undo. **Don't create the file on your own initiative** — propose it, and let an explicit ask, an
existing ADR folder, or acceptance of the proposal be what actually creates it; a repo's own
no-unsolicited-docs policy, where one exists, wins over this block's default. Stay publishable
(rule C): an ADR contains no secret and no client name, only the technical decision.

## Origin
Rewrite of the `documentation-and-adrs` skill from a market generalist dev skill catalogue; the ADR
template (six fields) and the "never delete, always supersede" rule are taken as-is, rewritten to
the mentis template. Section 4 comes from a `preserving-productive-tensions` skill in a market skills
repository: the idea that some tensions are load-bearing and shouldn't be resolved is real, but as a
standalone block it had nowhere to attach, so it's reduced here to the one place it changes behaviour —
a `simplify` pass about to collapse a trade-off somebody chose.

**"When" and the Output/Guardrails corrected 2026-08-11** against the real, installed
`xefi-claude-skills` `global` plugin (`no-project-docs`), read directly: "An architecture decision
record is not automatically an exception. If the user wants one, write it; do not volunteer it."
This block's original phrasing ("as soon as a structural decision is taken... an ADR file created")
had the agent spontaneously committing a new doc file the moment a decision qualified — exactly the
shape of unsolicited documentation the real house policy exists to refuse. The six-field template
and the never-delete-supersede rule are unaffected: they govern what a *written* ADR looks like,
not whether one gets written without being asked.
