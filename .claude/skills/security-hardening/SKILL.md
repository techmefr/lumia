---
name: security-hardening
description: Use when writing code that crosses a trust boundary (user input reaching a query or a template, a file upload, a new endpoint, an outbound call with a user-supplied target), the checks to apply while writing rather than at audit time. The writing counterpart to the seraph agent, which audits after the fact; auth, sessions and permissions are in auth-session-conventions.
---

# security-hardening

Step 6 of the pipeline (`WORKFLOW.md`). The distinction that keeps this block from duplicating
others: `seraph` **audits** a repo after the fact, `auth-session-conventions` owns **auth**, and this
block is what you apply **while writing** the code, on every other trust boundary.

A trust boundary is any point where data you don't control meets something that acts on it: a query,
a template, a filesystem path, a shell command, an HTTP call, a deserialiser.

## When
As soon as a diff has user-controlled data reaching one of those, adds a file upload, adds an
endpoint, or brings in a new dependency. Not as a generic pass over untouched code: that's `seraph`'s
job, on demand.

## Steps

### 1. Input: validate at the edge, on a whitelist
1. **Validate at the boundary, once, against an explicit shape** (a DTO, a schema), and let the inner
   layers trust the validated type. Checks scattered through the call chain get skipped by the one
   path nobody thought about.
2. **Whitelist, don't blacklist.** Enumerate what's allowed; a denylist of bad values is a promise to
   have thought of everything.
3. **Validate what the value *is*, not just its type.** A string that will be used as a sort column,
   a file path, a redirect target or a hostname must be checked against a known set of legal values,
   not merely confirmed to be a string.

### 2. Output: the escaping depends on the destination
1. **Never build a query by concatenation.** Parameterised queries or the ORM's binding, always,
   including for the parts that "can't" contain user data. Column and table names can't be
   parameterised at all, which is exactly why they go through a whitelist (§1.3).
2. **Escape for the context you're writing into.** HTML, an HTML attribute, JavaScript, a URL and SQL
   all escape differently; the framework's default usually covers HTML text and nothing else. The
   moment you reach for the "render this unescaped" facility, the value has to be sanitised or come
   from a trusted source.
3. **Never pass user data to a shell.** Use the API that takes an argument array; string interpolation
   into a command is not fixable by escaping.
4. **A user-supplied URL fetched server-side is SSRF, not just injection.** The trust boundary named at
   the top of this block ("an HTTP call") means an allowlist of destinations/schemes, a block on
   internal/link-local/loopback and cloud-metadata IP ranges (`169.254.169.254` and equivalents), and no
   blind following of redirects — a redirect can retarget an already-validated URL to an internal one
   after the check has passed.

### 3. Access control on every new route
1. **Every endpoint declares its authorisation**, and new endpoints are the ones that get forgotten:
   a route added to an already-protected controller inherits nothing automatically in some frameworks.
2. **Check ownership, not just authentication.** A logged-in user requesting record 42 must be shown
   to be entitled to record 42. Enumerable identifiers make this the most commonly exploited flaw in
   an otherwise well-authenticated app.
3. **Scope in the query.** Detail in `auth-session-conventions` §3.3: filtering after fetching means
   the data was already read, and one branch that forgets to filter leaks it.

### 4. Files, secrets and dependencies
1. **Uploads**: validate the type from the content rather than the filename or the client-supplied
   MIME type, cap the size, and store outside the web root with a generated name. Never build the
   storage path from user input.
2. **Secrets** come from the environment or a vault, never a literal in the code, never a fallback
   default in a config file, and never committed "temporarily". Detail on keeping them out of logs is
   in `auth-session-conventions` §2.4.
3. **A new dependency is a decision**: check that it's maintained and that the functionality genuinely
   isn't in the standard library or in something already installed. Every dependency added is code
   you now ship and don't review.

### 5. Verification
1. Replay the boundary with a **hostile value**, not just an invalid one: a quote and a
   semicolon where a name goes, a `../` in anything path-shaped, a script tag in anything rendered.
2. Replay the new endpoint **as a user who shouldn't have access** and as one who should, and confirm
   the refusal is clean rather than a crash or an empty success.

## Output / checkpoint
For each boundary the diff introduces: where validation happens, what the whitelist is, how output is
escaped, and the authorisation applied. The hostile-value and wrong-user replays observed, with
evidence, not reasoned about.

## Guardrails
- **Never weaken a check to make something work.** If a guard blocks a legitimate case, the whitelist
  is wrong: widen it deliberately, don't remove it.
- **Never disable escaping to fix a display bug.** Fix the data or sanitise it.
- Never test an injection against a shared or production environment: hostile-value replays belong in
  local or preview environments (that boundary is `seraph`'s rule too, and it applies to writing code
  just as much as to auditing it).
- Scope: this block covers application code. Platform hardening (TLS, WAF, network policy, IdP
  configuration) is infra reality and stays outside this repo.

## Origin
Rewrite of the `security-and-hardening` idea from a market generalist dev skill catalogue, which sat
unwritten in our backlog on the assumption that `seraph` and the native `/security-review` already
covered it. They don't cover the same moment: both look at code that already exists, and neither is
consulted while the boundary is being written. Underlying references are OWASP (Top 10, ASVS) and
OWASP's cheat-sheet guidance on escaping per context. The split enforced here — auth in its own
block, audit in `seraph`, writing-time checks here — is ours, and exists so that three blocks don't
restate the same OWASP list in three places.

Coverage check against OWASP Top 10 (2026-08-10): A02 (cryptographic failures) and A07
(identification/auth failures) stay out deliberately — they're `auth-session-conventions`' boundary, not
this one, per the split above. A09 (logging/monitoring failures) stays out too — that's
`observability-instrumentation`'s boundary. §2.4 (SSRF) was added because A10 was a real gap: the
trust-boundary definition already named "an outbound call with a user-supplied target" but no step
covered it, the one item on this list this block actually owns and hadn't written yet.
