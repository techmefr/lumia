---
name: code-baseline
description: Use when writing or reviewing code in any language, for the rules that hold regardless of stack, no comments, no god classes or bag-names, a file size ceiling with its exclusions, domain-specific exceptions instead of generic ones, every external API behind a client we own, parsed files wrapped in typed objects, distinct domain concepts as distinct types, no ticket references or AI attribution in the code, the test obligations on new behaviour including diff coverage, and preferring the narrowest supported extension mechanism over copying or replacing a third party's file. Carries the scope stance every one of those rules depends on, new code only, legacy untouched unless asked.
---

# code-baseline

Step 6 of the pipeline (`WORKFLOW.md`), and a reading angle at `review` (8). These are the rules that don't
change with the language, so each per-stack block (`laravel-conventions`, `python-conventions`,
`react-nextjs-conventions`, `vue-nuxt-vuetify-conventions`, `dotnet-conventions`, `go-conventions`,
`java-conventions`, `flutter-conventions`, `nestjs-node-conventions`, `php-patterns`,
`typescript-patterns`) can stop restating them.

**Relation to an org skill catalogue.** Where a company ships its own cross-language rule set, it is the
authority on the numbers (its file-size ceiling, its coverage floor) and overrides this block. The thresholds
below are stated as defaults with the reason attached, so a project can move one deliberately rather than by
drift.

**Applying an override is silent.** Write the code the governing rule actually requires and move on — never
report "a conflict between mentis and the house catalogue" to whoever's watching. That framing reads as
broken to a non-technical stakeholder even when the case is a normal, resolved one, and has already caused a
real project to get abandoned and restarted over nothing. Surface it as a specific, named question only when
no rule anywhere actually resolves the case — never as a general alarm.

## §0 The scope stance: read this before applying anything below
Every rule here governs **new and modified** code, and that limit is part of the rule, not a softening of it.
It is stated once, here, because all eleven depend on it:

1. **Never refactor existing code to satisfy one of these rules unprompted.** A 400-line controller, a
   12-method `*Service`, a file full of comments, a generic `throw` — they stay. A drive-by cleanup during an
   unrelated task is expensive to review, risks behaviour nobody asked to change, and is scope the requester
   didn't grant.
2. **But never *extend* the violation either.** Asked to add a behaviour whose obvious home is a god class,
   the answer is a new well-named class, not a thirteenth method. A new `throw` in a file full of generic ones
   still gets a named exception class. "Consistency with the surrounding mess" is how a codebase never
   improves.
3. **Bundled cleanup is fine, drive-by cleanup is not.** If you're editing the lines *around* a forbidden
   comment or a ticket reference, remove it in that same edit. If you're not touching those lines, leave it.
4. **Flag what you left, once, in the closing message** — the file that's now over the ceiling and where its
   seam is, the stale comment that contradicts the code, the missing coverage tooling. A finding stated is a
   decision handed to the human; a finding silently fixed is a decision taken from them.
5. **An explicit instruction overrides any rule here, without argument.** "Just put it in the service for
   now", "skip the coverage check", "throw a plain exception here, I know" — do it, and don't re-litigate.
   These are defaults for when nobody has decided, not a policy to enforce against the person asking.

## When
On every code edit, in any language. Checked at `gate` (7) and `review` (8).

## Steps

### 1. Comments
1. **No comments.** The one exception is a documentation block attached to a declaration — a function,
   method, class or module. Nothing else: no inline comment in a body, no comment above a statement, no
   end-of-line note, no commented-out code, no "why" comment.
2. The reason isn't aesthetic. **Nothing verifies a comment**: the compiler and the tests verify the code, so
   every comment is a future lie waiting for the next refactor. And a comment explaining code is a
   confession that the code is unreadable — the fix is the code.
3. **The three replacements, in order**: *rename* (a `// days until expiry` note next to `$d` disappears when
   the variable becomes `$daysUntilExpiry`); *extract a well-named function* (two statements wanting a
   `// validate then charge` note become `validateThenCharge()`); *restructure* until the shape carries the
   intent — early returns instead of a `// happy path` marker, a named constant instead of a `// 30 days`
   note.
4. **No ticket, story or issue identifier anywhere in the code** — not in a docblock, not in a variable,
   method or test name, not as "the story" or "user story 4.2". A tracker key describes *when* the code was
   written, not what it does, and it dies with the tracker. It belongs in the commit message, the MR
   title/description, and therefore in `git blame` — which is where anyone tracing a line will actually look.
5. **No AI attribution**: no co-author trailer naming an assistant, no "generated with" footer in a commit or
   MR body, no `@author`/`// AI-assisted` note in the code. Authorship records the **accountable human** —
   the engineer who reviewed it and will be asked about it. It also keeps `git blame` and contributor stats
   readable. Two carve-outs: a **real human** pair genuinely gets a co-author trailer, and existing commits
   that already carry an AI trailer are **never** rewritten (rewriting published history to strip a line is
   worse than the line).

### 2. Size and shape
1. **A new source code file stays under ~200 lines.** Past that, the edit that would cross the line is the
   moment to split.
2. **What the ceiling applies to**: application code (controllers, components, services, jobs, listeners,
   presenters), business logic, and utilities that hold real logic.
3. **What it explicitly does not apply to** — and mis-classifying to dodge the rule is itself the
   anti-pattern: config files and lockfiles (not authored), **tests** (a 600-line test class accumulating
   cases is not a smell), **migrations** (one atomic change per file, splitting defeats the point),
   markdown, generated or vendored files, and **declarative manifests** (route files, config arrays,
   registries — they're lists, and a long list is fine). A 700-line class isn't "config" because someone
   named it a config.
4. **How to split**: find the seam (which section is least tied to the rest), extract a **cohesive unit** (a
   class, a component, a module — not a random bag of functions), name the new file after its
   **responsibility** rather than its origin (`PriceFormatter`, not `OrderControllerHelpers`), then run the
   tests — a split is a refactor.
5. **Splitting to satisfy the count is worse than being over it.** A 195-line file is fine. A 210-line file
   with one coherent purpose and no real seam is fine — flag it rather than vandalise it. `Part1`/`Part2`
   files, and a `Helpers`/`Utils` dumping ground, are both re-entry points for the same problem.
6. **No god class, and no bag-name.** A class named `*Service`, `*Repository`, `*Manager`, `*Helper`,
   `*Util`, `*Handler` invites unrelated methods to accumulate, because nothing in that name can ever be "not
   about that". Name it after **what it does**: an action (`RegisterUser`), a query (`UsersDueForRenewal`), or
   a domain concept with real behaviour.
7. **The smells that flag one**: the bag name itself; more than ~3–5 public methods on the same noun for
   unrelated reasons; verbs from different domains on one class; 6+ injected collaborators; methods that
   never touch instance state (then it's a namespace, not a class); and a test file with five unrelated
   describe-blocks under one name.
8. A single-method `*Service` is the same mistake, smaller: if it does one thing, name it after that thing.
   And a "catalog interface" listing twelve `find…` shapes is the anti-pattern abstracted rather than fixed.
9. **The rule applies to the test tree too**: a helper used by one test file stays a local builder in that
   file; a helper genuinely reused across files gets a named fixture file — never a shared catch-all.

### 3. Errors
1. **Never throw a language built-in with a message string** (`Exception`, `RuntimeException`, `Error`,
   `ValueError`). Define a named class that describes the failure and throw that.
2. **The reason is catch-by-type versus catch-by-message.** `catch (UserNotFoundException)` survives a
   refactor; matching on `"user not found"` breaks the day someone improves the wording. It also gives you:
   typed context on the exception (`->userId`, `->validationErrors`, `->retryAfter`) instead of details
   stringified into a message and re-parsed; a clean mapping layer (not-found → 404, validation → 422); a log
   line that reads as a known domain outcome rather than a crash; one greppable name that finds every throw,
   catch, test and mention; and a stable assertion in tests.
3. **A hierarchy** when several failures share a category, so a caller can catch the category or the specific
   case.
4. **Four disguises that don't count.** A single mega-exception with a `code` field (enum-as-exception: it
   loses every benefit above); a catch-and-rethrow that wraps into a generic type (wrap into a *named* one);
   two throws differing only by message; and a project-wide `class AppException extends Exception` that
   everything throws — a rename, not a design.
5. An error crossing a public boundary is part of that boundary's contract, and gets the same care as a
   return type (`python-conventions` §2 for the failures-as-values form).

### 4. Boundaries
1. **Every call to an external HTTP API goes through a dedicated client object** — never a raw
   `Http::get` / `fetch` / `axios.get` / `requests.get` at a call site. The client owns the base URL (from
   config), authentication (token attachment, refresh, signing), the timeout and retry policy, the mapping
   from HTTP status and error payload to **named exceptions** (§3), and the typed request and response shapes.
2. **The order to choose it in**: the vendor's **official SDK** if one exists — don't reimplement what the
   provider maintains; otherwise a **thin client inside our own codebase**; and **avoid unofficial community
   wrappers** whose maintenance you don't control. An in-project client you own beats a stranger's abandoned
   one.
3. **This is rule B in code** (`CONVENTIONS.md`): the third party's breaking change hits one file. Scattered
   raw calls mean the endpoint is hard-coded in three places, one call site forgets the auth header (a silent
   401 in production), timeouts drift so the same outage looks different from each site, error handling is a
   coin flip per site, every consumer reads `body['data']['user']['id'] ?? null` with the schema living in
   people's heads, and the tests fake five different HTTP shapes instead of one client.
4. One client per external system, not one per endpoint. A class talking to three APIs is a god class (§2.6).
5. **Where a client is overkill**: a one-off maintenance script hitting one endpoint once; a **webhook
   receiver** (the API is calling *us* — we're the server, there's no client); a liveness ping that only reads
   200/non-200; and pre-production exploration in a scratch file before the client's shape is known.
6. **Anything parsed from disk or the wire is wrapped in a typed object** before use — a config file, a
   manifest, a plugin descriptor, a schema. A class with named accessors, a struct, a validated model,
   immutable by default.
7. The reason is the same shape as §4.3: `data['name']` may be a string, null, absent or a typo **at every
   call site**, while an accessor is checked once; the parse call stops being scattered; a default lives on
   one accessor instead of being duplicated as `?? 'layer'` five times and diverging; a derived value (split
   a `vendor/package`, slugify, normalise case) is a method rather than a repeated expression; renaming a key
   in the file becomes a one-class change; and the IDE and the type checker stop going dark, which they do
   the moment a raw map escapes.
8. **Validation has a home**: the factory fails fast on a missing required field or a wrong type, instead of
   each consumer inventing its own "is this safe to read" check.
9. **Where wrapping is overhead**: a single read at a single call site in a short script; data the program
   intentionally treats as opaque; and very large or streamed files, where materialising one object is the
   wrong move.

### 5. Domain types
1. **Distinct domain concepts stay distinct types**, even when structurally identical today. Two status enums
   sharing four values are two enums.
2. **Because they diverge.** Invoice statuses and order statuses look alike until one grows `refunded` and
   the other `returned`; then the shared type admits states each consumer must defensively ignore, and adding
   an order-only value re-tests and re-reviews every invoice consumer. A `Status` that means two things also
   can't be read locally — you must know which domain you're in first.
3. **The smells**: a generic name (`Status`, `Type`, `Kind`, `State`) shared across unrelated domains; one
   enum whose values are partitioned by a comment; domain-B fields added to a model named after domain A;
   **nullable columns that only apply to one subtype** (half the rows always null — that row is really two
   row-types crammed into one table); a method or foreign key that only makes sense for some rows; and a
   `match` with arms for values that "can't happen here".
4. **What to share instead**: genuine commonality goes through behaviour — a shared interface, a trait, a
   value object — never a fused type.
5. **What genuinely is shared**: a real single concept reused (`Money`, `Address`, `DateRange`), and
   **cross-cutting technical types** — ids, timestamps, audit fields, pagination wrappers, soft-delete flags.
   Those aren't domain concepts; share them freely.

### 6. Tests owed by new code
Stated here because it's language-agnostic; the doctrine of *how* to test lives in `skills/tdd` and in the
testing package it points at.
1. **New behaviour ships with a test** — a function, endpoint, controller, job, listener, command, model
   event, domain rule, composable, component or page. No exceptions by language.
2. **A test is done when it has been run and its output read**, not when it's written. What running catches
   that reading never does: a wrong import or missing fixture, a typoed matcher, a stale factory, a missing
   test-env variable or migration, an assertion that can never fail, and a test that passes for the wrong
   reason because nothing was actually exercised.
3. **Fix the right side.** The test is wrong (matcher, setup, expectation) → fix the test. The code is wrong →
   the test just did its job; fix the code if scope allows, otherwise flag it. Both look right → re-read the
   test. **Never weaken the assertion to get green**: turning `toEqual(42)` into `toBeGreaterThan(0)` is a
   regression disguised as a fix.
4. **Verify an expected-failure test fails for the stated reason**, not for a setup error that happens to
   throw.
5. **Six ways to fake it, all refused**: claiming "tests added" without running them; weakening an assertion;
   skipping or deleting the failing test you just wrote; re-running until it passes by chance (an
   intermittent pass means broken, and the flake is the bug); silencing the runner (`2>/dev/null`,
   `|| true`); and asserting on a value the test itself just set (`create(['name' => 'Bob'])` then asserting
   the name is Bob tests the factory, not the code).
6. **If you genuinely can't run them** — no environment, no database, a sandbox that forbids it — **say so
   explicitly** in the closing message. An unrun test presented as passing is exactly what the pipeline's
   default-is-failure guarantee exists to catch (`WORKFLOW.md` §3, and `hooks/verify-gate.sh` refuses a
   `passes: true` claim with no read evidence).
7. **The coverage bar is on the diff, not the project**: ≥80% of the lines added or changed exercised by a
   test in the same change. It works at 10% total coverage or at 100%, it can't be satisfied by tests written
   years ago, and it ratchets the total up on its own. It also gives a bugfix its regression test for free —
   the lines you touched to fix it are changed lines.
8. **What doesn't count as covering it**: coverage-ignore annotations added to make the number pass; an
   assertion-free test that only touches lines; snapshotting a whole rendered page to cover one helper;
   padding the change with tests for files you didn't touch; constructor-only tests of behaviourless DTOs;
   and lowering the project's CI threshold — that's a project decision, never a side effect of your change.
9. **Where the bar doesn't apply**: a pure refactor with no behaviour change (the existing tests should
   already cover it — if they don't, that's the finding); framework boilerplate and generated scaffolding;
   a behaviourless DTO or value object; an exception class that only carries a message; and the first commit
   in a brand-new repo, where the coverage tooling doesn't exist yet.

### 7. Customising a third party
1. **Changing a package's, framework's or generator's behaviour by copying and editing its file, or
   replacing it outright, is the last resort — not the first move.** Narrowest first: a single config
   key/flag, a documented config file, a documented file-override hook, a wholesale file replacement,
   forking/patching the vendor code. Stop at the first tier that reaches the goal.
2. **Investigate before overriding, every time**: identify the exact package and version, read its docs
   for config keys/env vars/lifecycle hooks/extension points, and if the docs are thin, read the source
   — how it loads user config, at which layer a default applies (build vs runtime, merge vs whole-file
   replace). Skipping straight to "just replace the file" is usually a config key not yet found.
3. **A whole-file override that only replaces part of the upstream file is a latent bug**: it silently
   drops whatever else the package's default provided, surfacing far from the edit that caused it. A
   whole-file replacement reproduces the upstream file faithfully and changes only what's needed.
4. **When wholesale override genuinely is the answer** (confirmed from the docs or source that no
   narrower hook exists), say so in the code or the PR — the sentence that proves the investigation
   happened is what stops the next reader from re-deriving it, or reflexively "fixing" it back to a
   config key that was already ruled out.
5. **The tells that this rule was skipped**: copying a default/template file verbatim to change one
   line; editing a file inside a package/dependency directory directly; a duplicated upstream template
   that will drift the moment the package updates; reaching for "replace the whole thing" without having
   checked for a config key first.

## Output / checkpoint
No separate checkpoint: this is the floor `gate` (7) and `review` (8) check on every diff. A finding here is
not a nit — each rule exists because its violation was expensive. What it owes at review: no new comment or
ticket key, no new bag-named class, no new generic throw, no new raw external call, no new raw parsed map
escaping its reader, and the diff's own lines covered by tests that were actually run.

## Guardrails
- **§0 is not optional.** Applying any rule below it to legacy code, unprompted, is the failure mode of this
  block — it turns a discipline into an unrequested refactor.
- **Never mis-classify a file to dodge the ceiling**, and never split one purely to satisfy the count.
- **Never weaken, skip or silence a test to turn the bar green**, and never edit the project's coverage
  threshold as a side effect.
- **Never rewrite git history** to remove an attribution trailer.
- Where an org rule set is installed and its numbers differ, **its numbers win**.

## Origin
**An org skill catalogue's cross-language rule set (14 skills: no comments, no ticket references, no AI
attribution, file size limit, no god classes, no generic exceptions, external APIs behind an owned client,
parsed files as typed manifests, distinct concepts as distinct types, layered architecture, test new
features, run generated tests, diff coverage, plus one on not exporting the catalogue itself)** — read in
full, then extracted, de-identified and rewritten generically, with everything naming an internal repository,
package or channel deliberately left out (rule C). The catalogue-export rule was **not** carried over: it
governs that catalogue's own distribution, not code.

The layered architecture rule was **not** duplicated here: it already lives in `skills/archi` and
`skills/domain-modeling`, and the per-stack blocks carry the language form of it.

**Deepened 2026-08-06.** A first pass wrote this block from the skills' descriptions alone. Reading the
bodies added what mattered most and what a summary loses: **§0's scope stance** (new code only, legacy
untouched, bundled versus drive-by cleanup, flag-don't-fix, and the user's local override — a coherent
posture that appears in every one of those skills and that the descriptions never state), plus the exclusion
lists, carve-outs and anti-pattern catalogues throughout. Stamped 2026-08-06.

**§7 added 2026-08-11** from the same catalogue's `extend-dont-override`, a 15th skill added there after
this block's original mining pass (confirmed absent from the "14 skills" counted above). Read directly
from the installed plugin rather than from a description alone, since the source itself is short enough
that the body is the whole rule: the preference order (config key → config file → override hook → whole-file
replace → fork) and the "state why no narrower option worked" discipline are taken as-is and rewritten
generically, with the source's Railpack/`php.ini` worked example left out (rule C — a specific vendor tool,
not a mechanism worth naming here).
