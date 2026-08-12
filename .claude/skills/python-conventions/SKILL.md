---
name: python-conventions
description: Use when writing or reviewing Python, type hints and mypy strict, explicit None checks, failures returned as values at public boundaries, naming that reveals intent, async correctness, the toolchain (ruff, uv, mypy, pytest), dependency injection with explicit lifetimes, layered project structure, configuration, and the ORM rules (no DB-side cascade, Python-side defaults, no implicit lazy loading, enums over magic strings). Self-contained, it assumes no plugin or catalogue installed.
---

# python-conventions

Step 6 of the pipeline (`WORKFLOW.md`). Frames the writing and review of Python code. **Special status**:
like `go-conventions`/`dotnet-conventions`, no production experience behind this block yet — content comes
from the PEPs, deterministic tooling (ruff, mypy) and an org catalogue for the stack, not from real review
feedback.

**Relation to an org skill catalogue.** Where a company ships its own versioned catalogue for this stack, it
is the authority on **its** house style — its framework, its internal support library, its pinned tool
versions — and overrides this block wherever the two differ. This block states the same rules with the
internal names removed, so they apply to a project that has neither.

**Applying an override is silent.** Write the code the governing rule actually requires and move on — never
report "a conflict between mentis and the house catalogue" to whoever's watching. That framing reads as
broken to a non-technical stakeholder even when the case is a normal, resolved one, and has already caused a
real project to get abandoned and restarted over nothing. Surface it as a specific, named question only when
no rule anywhere actually resolves the case — never as a general alarm.

## When
As soon as Python code is written or modified, during `code` (6) or `tdd` (5).

## Steps

### 1. Typing
1. Type hints on **all new code**: parameters, return types, class attributes, module-level constants. A type
   checker in strict mode (`mypy --strict`, `pyright`) runs on the diff, not only at project setup.
2. Existing untyped code stays as it is, grandfathered by a baseline. Typing is a rule for new code, not a
   licence to rewrite the codebase in passing.
3. **Never a bare ignore comment.** Every silencer carries the specific error code in brackets
   (`# type: ignore[arg-type]`) plus a short reason. A bare ignore hides every future error on that line too.
4. Explicit `T | None` rather than an untyped `None` default that leaves the real contract to guesswork.
5. A dataclass or a validation model for a data structure with rules, rather than an untyped dict passed from
   function to function. `TypedDict` to type an existing dict (external API, JSON) without converting it into
   a class — but never `dict[str, Any]` out of reflex.
6. On modern Python, the language's own generic syntax (PEP 695) rather than explicit `TypeVar`s, and a
   `Protocol` rather than an ABC for duck-typed collaborators.
7. Tests are the relaxed zone: annotations optional, loose types acceptable in expressions. Holding test code
   to production typing rules buys nothing and costs momentum.

### 2. None, failures, exceptions
1. **Never implicit truthiness where `None` is possible.** `if x:` is also false for `0`, `""`, `[]`, `{}` —
   so a valid empty value takes the missing-value branch. `if x is None:` / `is not None`, always.
2. **A public boundary returns its failures as values**, so the type checker can see them: `T | None` for a
   binary present/absent, a result/option type for richer typed failures. A boundary that raises its failure
   modes silently makes every caller guess which exceptions exist.
3. Inside a tightly-coupled module, helpers may raise freely — only the boundary is held to the rule.
4. Truly exceptional conditions still raise. Results are for **recoverable** failures; wrapping a
   programming error in a result type just delays the crash.
5. A raised exception is a specific class inheriting from `Exception`, never a bare
   `except Exception:` that swallows everything indiscriminately.
6. An `except` with no rethrow and no log hides a real bug: never silent, even as a last resort.
7. A context manager (`with`) for every resource that has to be closed (file, connection, lock): never a
   manual close an intermediate exception can skip.

### 3. Naming
1. A name reveals **intent** — what the value represents or what it's for. `tmp`, `data`, `result`, `arr`,
   `item`, `value`, `x` push the meaning into the reader's head; `column_value`, `user_to_import`,
   `pending_applications` state it.
2. **No magic strings or numbers with domain meaning.** A domain value (status, type, kind, mode) becomes an
   `Enum`/`StrEnum` and is typed as that enum on the model; a threshold or limit becomes a named constant.
   A literal `"pending"` compared in three files is three chances to typo it.

### 4. Async
1. `asyncio.gather` for independent operations, never a serial `await` in a loop out of reflex.
2. Never mix blocking code (synchronous I/O, heavy CPU work) into an `async` function without isolating it
   (`run_in_executor`): it blocks the whole event loop, not just the caller.
3. **An async application is async all the way down.** A synchronous database engine or client in an async
   path either blocks the event loop or fails at runtime with a greenlet/context error; use the async engine
   and session, with an async driver in the connection URL.
4. A coroutine created but never awaited or stored is a silent bug (`RuntimeWarning: coroutine was never
   awaited`), always checked.

### 5. Structure and style
1. Immutability by default: a mutable default argument (`def f(x=[])`) is banned — it's shared across every
   call, the classic trap.
2. `pathlib.Path` rather than string manipulation for file paths.
3. Comprehensions rather than a loop + `append` where readability gains, never nested to the point of hurting
   it.
4. Separate **functional/business** layers from **technical/infrastructure** ones (the layered split), with a
   predictable place per component and no technical layer importing a business one.
5. Every component declares its own wiring in one place (a provider/registration module) rather than
   scattering registrations across the app.
6. **Configuration: one file per namespace**, each exporting a module-level mapping, the filename being the
   namespace. Values are read through the config layer, never `os.environ` reached into from business code.
7. Reach for the project's existing support layer before the stdlib or a new dependency for something it
   already covers (password hashing, structured logging, config access, encryption, events, DI, test
   scaffolding). A second way to do a solved thing is the duplication that bites later.
8. Re-checked directly against PEP 8 and ruff's default rule set on 2026-08-10: re-verified, unchanged —
   the PEP 8 items that carry a real judgment call (naming, truthiness, mutable defaults, comprehensions,
   context managers) were already covered above; everything else it states is pure style ruff already
   auto-fixes (import order, f-strings over `%`/`.format()`, `enumerate` over `range(len(...))`), the same
   reason this block never restated PSR-12-style formatting the way `php-patterns` didn't.

### 6. Dependency injection and lifetimes
1. A binding's default is an application-lifetime singleton. Reach for a different lifetime **deliberately**:
   per-request scope for per-request state, transient for a fresh instance per resolution.
2. Per-request state in an app-lifetime singleton is the same captive-dependency bug as anywhere else: it
   leaks one request's data into the next.
3. Overriding or wrapping another module's binding is legitimate but explicit, in one place, so the effective
   graph stays readable.

### 7. ORM and migrations
1. **No DB-side cascade delete** (`ondelete="CASCADE"`): the database bypasses the ORM, so delete events and
   registered listeners never fire on child rows. Cascade in the ORM layer, where the hooks live.
2. **Python-side defaults over server-side defaults**: a Python default is visible at the call site, testable
   without a database, and applies whether the row came from the ORM or a raw insert.
3. **No implicit lazy loading in an async ORM**: declare relationships non-loading (or raising) so the caller
   states what it needs. Implicit lazy loading is both a runtime failure in async contexts and the root cause
   of N+1 queries.
4. A query inside a loop is an N+1: load what you need in one query before iterating.
5. Transactions go through one entry point (a single transaction/session facade), with after-commit work
   registered explicitly rather than run inside the transaction and hoped to be atomic with it.

### 8. Toolchain and tests
1. One formatter+linter (ruff), one dependency and Python-version manager (uv), one type checker (mypy
   strict), one test runner (pytest) — **pinned**, and the same versions in CI as locally. A tool floating on
   `latest` turns an unrelated release into a red build.
2. The pytest plugin set is pinned in a dev group and configured in one block, not rediscovered per developer.
3. Test doubles substitute a collaborator **through its own public seam** (the facade's or the container's
   double/override), never by patching internals: a test patching a private path breaks on any refactor and
   proves nothing about the contract.
4. A test that needs the application built goes through the project's test base, so the container, the
   config and the database context are set up the same way in every test.
5. For the doctrine of *what* to test — plan first, exhaustive rather than happy-path, the persona/permission
   matrix, the coverage floor — see `skills/tdd`; this section is only about the tooling.

## Output / checkpoint
Code compliant with the sections above, and `ruff check`/`mypy` (or `pyright`) with no new finding introduced
by the diff. Checked by `gate` (7) and `review` (8).

## Guardrails
No comments in the code produced. This block hasn't been confronted with a real production Python project
yet: if a rule here diverges from a real observed need, fix this block rather than treating it as settled.
These rules govern **new** code; existing untyped, sync or magic-string code stays until migrated
deliberately. Where an org catalogue is installed and disagrees, **it wins**.

## Origin
Ideas taken from: PEP 484/526/604/695 (type hints, generics), PEP 8 (style), ruff (default rule set, replaces
flake8/isort/pyupgrade), mypy/pyright (strict typing); **an org skill catalogue for this stack (20 skills:
type hints on new code, explicit `is None`, failures as values at boundaries, intent-revealing naming, magic
strings as enums, async-first data access, DI lifetimes, layered component layout, config per namespace,
transactions through one facade, no DB cascade, Python-side defaults, non-loading relationships, facade-based
test doubles, application test base, ruff/uv/mypy/pytest toolchain)** — rules extracted, de-identified and
rewritten generically, with the internal framework and support-library names deliberately left out (rule C).
Mechanisms rewritten, no copied text. Stamped 2026-08-06.
