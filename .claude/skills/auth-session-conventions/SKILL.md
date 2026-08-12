---
name: auth-session-conventions
description: Use when touching authentication, sessions, tokens or permission checks (login, refresh, logout, guards, middleware), the rules that keep an auth flow from breaking silently. Complements api-design (contracts) and the per-stack conventions blocks (idiomatic code) on the one surface where a regression is invisible until it locks users out.
---

# auth-session-conventions

Step 6 of the pipeline (`WORKFLOW.md`), on the auth surface specifically. Auth is the one place
where a regression **doesn't show up as a failing test**: the happy path keeps working, and the
breakage only appears an hour later when the first token expires. This block exists because that
already happened to us: a refresh flow broken by a change, shipped, and left broken because
nothing in the normal loop observed it.

## When
As soon as a diff touches: a login/logout route, token issuing or renewal, session storage, an
auth middleware/guard, or a permission check. Also when adding a first protected route to a
service that had none.

## Steps

### 1. Token lifecycle: the expiry path is part of the feature
1. **Test the flow after expiry, not just after login.** A login that works proves nothing about
   the refresh. Force the expiry (shorten the TTL in a dev config, or fast-forward the clock) and
   replay the journey: this is the only way to observe the renewal path.
2. **One refresh in flight at a time.** Several parallel requests hitting a 401 together must not
   each fire their own refresh: queue them behind a single renewal, then replay them. Mechanism in
   section 4.7, including the cross-tab case that a shared promise doesn't cover.
3. **A failed refresh logs out cleanly**, it never retries in a loop: a refresh that 401s and gets
   retried indefinitely spins forever and hides the real cause.
4. **The expiry margin is explicit**: renew shortly *before* expiry, never exactly at it, or clock
   skew between client and server produces intermittent failures no one can reproduce.
5. **A permission/role change invalidates the current token, it doesn't wait for it to expire
   naturally.** A demoted or revoked user keeps acting on their old permission set for the rest of
   the token's TTL otherwise — the refresh renews the token, it doesn't re-derive it from the user's
   *current* state unless the backend forces that on the next refresh/request.
6. **An absolute session lifetime, on top of the rolling per-token TTL.** The refresh mechanism can
   otherwise renew a session indefinitely as long as the user stays active, which is a different
   guarantee from "expires N minutes after issue": a hard cap forces re-authentication periodically
   regardless of activity, bounding how long a hijacked session stays usable.

### 2. Storage and transport
1. **Never a token in a URL, in any form.** Not in the path, not in the query string, not in a
   fragment. A URL is copied into server access logs, into browser history, into the `Referer`
   header sent to third parties, and into every proxy and analytics tool on the path. The only
   credential allowed to travel in a redirect URL is a **short-lived, single-use authorization
   code**, exchanged once against the backend (see the reference flow below). This is the one rule
   in this block we hold against pressure: some teams do ship SSO by handing the token over in the
   redirect URL, and adopting it "to be consistent with them" would be adopting the leak.
2. A token lives in a cookie (`Secure`, `SameSite`), never in `localStorage`: `localStorage` is
   readable by any injected script and survives with no expiry semantics. **Why this pattern isn't
   also a CSRF exposure**: classic CSRF relies on the browser attaching a cookie *automatically* to a
   cross-site request; here the frontend reads the cookie in JS and attaches it itself as a `Bearer`
   header, so a forged cross-site request arrives with no `Authorization` header at all.
   `SameSite=Strict`/`Lax` is still set (defence in depth, and it's what stops the cookie itself
   being read cross-site), but the CSRF question is answered by the transport shape, not by a
   separate CSRF token.
3. **Known trade-off in our own pattern, stated rather than hidden**: our frontends set that cookie
   client-side and attach the token themselves as a `Bearer` header, so the cookie is **not**
   `httpOnly` and an injected script can read it. `httpOnly` + a server-set cookie is strictly
   stronger and is the target for a new service that can be built that way. On an existing
   frontend, don't half-migrate: a token that's both in a JS-readable cookie and expected in a
   header gains nothing until the whole chain moves.
4. **Never a token in a log either**, and a clean URL doesn't get you this for free: the usual leak
   isn't the URL, it's logging a whole object that happens to carry the credential. Watch four
   paths in particular:
   - **HTTP client error objects.** A failed request's error carries the request config, headers
     included. `logger.error(err)` on it writes the `Authorization` header out in full.
   - **Exception reporters and breadcrumbs.** Crash/APM tooling serialises request headers and
     cookies by default: the allowlist/denylist has to be configured, not assumed.
   - **Debug dumps of a request** (curl-style replay lines, "request/response" trace logging):
     convenient precisely because they're complete, which is the problem.
   - **The token as a correlation key.** Never use it to tie logs together; that's what a
     correlation ID is for.
   Redact at the point of writing, on the field name (`authorization`, `cookie`, `set-cookie`,
   `access_token`, `refresh_token`), not by trusting call sites to pass the right thing. A token in
   a log is a valid credential sitting in a system with wider read access than the app itself, and
   with a much longer retention than the token's own TTL.
5. Logout **invalidates on the server side** too: clearing the client store while the token stays
   valid server-side is not a logout.

### 3. Authorisation: the check lives on the server
1. Every permission check is enforced **server-side**; the frontend check only hides UI, it never
   grants anything: hiding a button is not a permission.
2. The permission name is verified against what the backend actually exposes, never guessed from
   the feature's name: a guard wired onto a permission that doesn't exist fails open or fails
   closed depending on the framework, and both are bugs.
3. Scoped access (per tenant/agency/organisation) is applied **in the query**, not filtered after
   the fact: filtering in the response means the data was already fetched, and one forgotten branch
   leaks it.

### 4. Our reference login flow
This is the shape already in production on two of our Nuxt frontends against a Laravel backend.
A new frontend follows it rather than inventing a variant.

1. **Provider redirect.** The `/login` page hands off to the identity provider. The frontend holds
   no password and never sees one.
2. **Callback with a code.** The provider returns to a dedicated callback route carrying a
   short-lived `code` in the query. That page renders nothing but a progress state.
3. **Exchange, once.** The callback exchanges the code against the backend for an access token.
   Guard the exchange with a single-flight promise: a callback page can mount twice (a client
   remount, the user refreshing) and a single-use code replayed a second time fails, logging the
   user out at the exact moment they were logging in.
4. **Token into a cookie, then a Bearer header.** The API layer reads the cookie and attaches
   `Authorization: Bearer …` to every call. A `401` from any call triggers logout, in one place
   (the API plugin), not per call site.
5. **Deny by default at the router.** A global route middleware protects every route, with an
   explicit allowlist of public routes (login, callback, error/waiting pages). New routes are
   protected because they're new, not because someone remembered to protect them.
6. **Typed auth outcomes, not a boolean.** The exchange and the refresh return an explicit state,
   distinguishing at minimum: authenticated, unauthenticated, **awaiting account approval**, and
   error. Each maps to its own destination. A boolean flattens "your account isn't approved yet"
   into "login failed", which sends the user to retry a login that can never succeed.
7. **Single-flight refresh, across tabs.** Both implementations dedupe the refresh, but not
   equally: an in-memory shared promise only dedupes inside **one** JS context, so two open tabs
   still fire two refreshes and can invalidate each other. The reference is the stronger one: a
   cross-context lock (`navigator.locks`) around the refresh, plus a `BroadcastChannel` so the other
   tabs **refetch the user** on the new token instead of racing for their own. An in-memory promise
   alone is acceptable only where a single tab is guaranteed, which in a browser it never is.
   Throttling the refresh (don't renew if the last one is very recent) is a useful complement, not a
   substitute: it narrows the race window without closing it.
8. **Teardown is complete.** Logout calls the backend, then clears local state in a `finally` so a
   failing call can't leave a half-session behind. Clearing means the token *and* everything derived
   from the identity: user, permissions, feature flags, and the domain state scoped to that user.
   A leftover scoped selection is what leaks one user's context into the next session. The
   `Clear-Site-Data` response header on the logout call is the browser-level equivalent for anything
   the app itself doesn't track (cache, storage, service workers) — cheap insurance on a shared
   machine.

### 5. Verification before shipping
1. Replay the journey: login → expiry → refresh → logout, plus one protected route with an
   insufficient permission (expect a clean refusal, not a crash).
2. Replay it a second time **concurrently** (two tabs on the same session) if the diff touched the
   refresh: that's where the race shows up.
3. **Then search the logs the replay just produced** for the token value you were issued, and for
   `Authorization`/`Bearer`. A clean grep is the evidence; assuming the redaction works is not. Do
   this on the error paths too, since that's where whole objects get logged.

## Output / checkpoint
The expiry/refresh path was observed, not assumed: evidence attached (log, network trace, or
screenshot of the renewed request succeeding). No auth diff reaches `gate` with only the login
path exercised.

## Guardrails
- Never weaken a check to make a test pass: a test that only goes green with the guard removed is
  reporting a real problem.
- Never invent a permission name to unblock yourself: ask what the backend exposes.
- Rotating or revoking credentials/secrets in a shared environment is a **human decision**, not
  something the agent does on its own initiative.
- This block covers the application-level flow. Provider configuration (SSO, identity provider,
  realms) is infra reality and stays outside this repo.

## Origin
Gap found while scouting a market per-technology agent catalogue (separate `jwt`, `oauth-oidc`,
`keycloak` and `auth0` agents, with no equivalent anywhere in our roster), crossed with a
documented internal incident: a token refresh flow broken by a change, merged, and left broken
because the normal loop never observed the post-expiry path. The per-provider agents were **not**
retained (per-library fragmentation, against our per-role doctrine); what's kept here is the
flow-level discipline that the incident showed was missing. Transport rules follow OWASP
session-management guidance.

Section 4 is **not** sourced from the market: it's extracted from the two real implementations
already running on our own Nuxt frontends against a Laravel backend, read side by side. Where the
two disagreed, the stronger one became the reference and the reason is stated inline (single-flight
refresh: cross-context lock + cross-tab broadcast beats an in-memory promise). Where our own
practice is weaker than the generic rule, that gap is stated rather than smoothed over (§2.3, the
non-`httpOnly` cookie). The token-in-the-URL prohibition is written as a rule to hold precisely
because the surrounding practice on other teams goes the other way.

Re-checked directly against the OWASP Session Management Cheat Sheet on 2026-08-10: three real gaps
closed — renewal/invalidation on a privilege-level change rather than waiting for natural expiry (§1.5),
an absolute session lifetime on top of the rolling TTL (§1.6), and `Clear-Site-Data` on logout (§4.8).
The CSRF note in §2.2 was added the same pass: the cheat sheet leans on `SameSite` for CSRF defence,
which this block already set — what was missing was saying explicitly *why* the Bearer-header transport
closes the classic CSRF vector too, rather than leaving a reader to wonder if a CSRF token is also
needed. Session-ID-regeneration-at-login and idle-timeout ranges stay out: they're framed for a
server-side session store, and this reference flow is a stateless bearer token, where the equivalent
guarantee is already the expiry-margin/refresh discipline in §1.
