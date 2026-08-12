---
name: testing-anti-patterns
description: Use when writing or reviewing tests, the specific ways a test suite reports safety it doesn't have, mock theatre and timing guesses above all. Complements tdd (which says write tests first) by covering what makes a written test worthless.
---

# testing-anti-patterns

Step 5 of the pipeline (`WORKFLOW.md`), and a review lens at step 8. `tdd` says tests come first;
this block is about the tests that exist, run, pass, and prove nothing.

Every pattern here has the same shape: **the suite is green and the safety is imaginary**. That's
worse than having no tests, because nobody checks manually anymore.

## When
While writing tests, and when reviewing a diff that adds them. Also when a bug reaches production
through code that had coverage: one of these is usually why.

## Steps

### 1. Mock theatre: testing the double instead of the code
1. **Never assert on a mock's existence or on the mock having been called** as the point of the test.
   That confirms your mock works. Assert on what the code *does*: the value returned, the state
   changed, what the caller observes.
2. **Red flag, mechanical**: if removing the mock makes the test fail for a reason other than a
   missing dependency, or if the mock setup is more than half the test, the test is about the mock.
3. **Mock at the lowest useful level**, usually the external boundary (network, clock, filesystem),
   not a high-level method of your own code. Mocking your own method mocks away the thing under test.

### 2. Mock without understanding what you removed
1. **Before mocking, know the real method's side effects** and whether the test depends on them.
   Mocking away a call that the test silently relied on gives a pass that means nothing.
2. **An incomplete mock fails silently.** A double returning only the three fields you thought about
   passes, while the real payload has twelve and the code reads a fourth. Build mocks from the real
   response shape, not from the fields you remembered.
3. Corollary already learned the hard way on our own stack: a mocked engine missing a method the code
   calls produces a crash that looks like a real bug, and hours go into the wrong hypothesis.
4. **Run it against the real implementation once**, if you can, before deciding what to mock.

### 3. Timing guesses: the flaky-test engine
1. **Never wait for a duration; wait for the condition.** `sleep(50)` then assert is a bet on machine
   speed: it passes locally and fails in CI under load, which is the definition of flaky.
2. The correct shape is polling the thing you actually care about, with a **timeout** so a genuine
   failure fails instead of hanging, and a **sane interval** (10ms, not 1ms).
3. **Read the state fresh inside the loop.** Capturing it before the wait and re-asserting on the
   stale copy is the same bug with extra steps.
4. **A deliberate delay is only legitimate when the timing itself is the thing under test**, and then
   it gets a comment saying so — otherwise the next person deletes it or, worse, copies it.
5. Never "fix" a flaky test by increasing the sleep. That converts an intermittent failure into a slow
   suite that still fails, occasionally, for the same reason.

### 4. Test-shaped code in production
1. **A method that exists only for tests doesn't belong in the production class.** Reset helpers,
   internal-state getters, test hooks: move them into test utilities. Otherwise something eventually
   calls them for real.
2. Red flag: a public method whose only callers are in test files.

## Output / checkpoint
For the tests added: no assertion whose subject is a mock, no bare duration wait, mocks justified
against the real shape, no test-only method left in production code. If a test can't fail, it isn't
finished (see `dozer`, which owns this while writing).

## Guardrails
- **Never weaken a test to make it pass.** Loosening an assertion, widening a matcher or deleting a
  case converts a real signal into a green tick.
- Never mock "just to be safe": each double is a piece of reality removed, and it has to be justified.
- A flaky test is a **bug report**, not noise to be retried. Retrying it hides either a race in the
  test or a race in the code, and you can't tell which without looking.

## Origin
Rewrite of `testing/testing-anti-patterns` and `testing/condition-based-waiting` from a market skills
repository (the companion repo of the upstream this framework responds to), merged into one block
because they're one responsibility: tests that report safety they don't have. The five anti-patterns
and the wait-on-a-condition rule are theirs. The incomplete-mock item is reinforced by our own
experience of a mocked search engine missing a method, which presented as a database bug; the
"never increase the sleep" and "a flaky test is a bug report" formulations are ours.
