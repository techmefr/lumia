---
name: tdd
description: Use when the tests step starts, before any implementation code, write the tests first (test-casebook doctrine) and turn every acceptance criterion into a contract line that fails by default.
---

# tdd

Step 5 of the pipeline (`WORKFLOW.md`). Tests first, and a **default-FAIL contract** that will
make the GATE (step 7) mechanical.

**Where the doctrine lives.** The testing doctrine itself — `data-test-*` selectors, the `task-test.md`
plan, the permission/persona matrix, the coverage floor, the per-stack guides — is owned by the
`test-casebook` family (MIT, `techmefr/*`), which also ships its own executing agents and a
plan-before-tests hook. **Where it's installed, it is the authority and this block defers to it**; install
the sibling that matches the stack rather than restating its rules here — `test-casebook` for the frontend,
`test-casebook-back-js` for a Node backend, `test-casebook-back-php` for a PHP one, each `npm i -D` and
pinned. What stays ours
is the **default-FAIL contract** and its link to the gate — that has to hold in a repo with no package
installed at all.

## When
After `plan`, before writing the implementation.

## Steps
1. For **every acceptance criterion** in the spec, create a line in `test-results.json`
   initialised to `{ "passes": false }` (the contract starts as a failure).
2. Write the matching test following **test-casebook** (`data-test-*` selectors, exhaustive,
   persona matrix, target coverage ≥ 90%).
3. Run the suite: **everything is red**, that's the expected result at this step.
4. **Read each failure**: red has to mean the assertion failed, not that the test file crashed on a
   broken import or an incomplete mock. A setup error satisfies the contract while proving nothing,
   and it turns green later for reasons unrelated to the behaviour.

Delegate the writing to `dozer` (tests only, never implementation) when you want that separation
enforced rather than relied on. That separation is the whole defence against a specific failure mode:
the same agent that just wrote the implementation editing the test's expectation instead, later, to
turn a red result green. This block's guardrail (below) covers the moment these tests are **written**;
`code`/`debug` carry the sibling rule for the moment one of them **fails during implementation** —
adding a case is fine, loosening or retargeting an existing assertion to match broken output isn't,
whichever agent is at the keyboard.

## Output / checkpoint
`tests_written` + `test-results.json` (every line `{ passes: false }`).

## Guardrails
No test bypassed, hidden or disabled. The default contract is **failure**: nothing is
"passing" until the GATE has proven it. Never loosen an assertion or lower a coverage threshold to
close a gap: a test that can't fail reports safety that isn't there.

## Origin
`test-casebook` (MIT, `techmefr/test-casebook`) for the doctrine, plus market long-running agent patterns
for the default-FAIL contract, rewritten. **Aligned with `test-casebook` 1.1.0**, `test-casebook-back-js`
1.0.0 and `test-casebook-back-php` 1.0.0 — all three published on npm at that version. The doctrine is
still only ever "as fresh as the copy installed in the project": a stamp here dates a reading, not the
installed package. Re-verify
against the installed package rather than from memory (`skills/source-freshness`). Stamped 2026-08-11.
