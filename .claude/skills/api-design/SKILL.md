---
name: api-design
description: Use when designing a new API/interface (REST, tRPC, GraphQL) before implementing it, contract-first, Hyrum's law (every observable behaviour ends up depended on), extension rather than breakage, short verification checklist before shipping the contract.
---

# api-design

Step 3 of the pipeline (`WORKFLOW.md`, between `archi` and `plan`), when the task is designing an
interface consumed by others (frontend, third-party service, another team): not for an internal
function with no public contract.

## When
Before implementing a new endpoint/route/procedure: never after the fact by "documenting what
already exists" (by then it's too late to steer the design).

## Steps

### 1. Contract-first
1. The typed schema (DTO, tRPC type, OpenAPI/GraphQL schema) is written **before** the
   implementation, not inferred from the code afterwards.
2. Validation placed **only at the boundaries** (the API entry point): internal code trusts the
   already-validated type, no deep revalidation that duplicates the logic.
3. A single system-wide error format (the same structure for every error returned), never a
   different format per endpoint.

### 2. Hyrum's law: whatever is observable will be depended on
1. Every observable behaviour (field order, default value, error format) will sooner or later be
   depended on by a consumer, even an undocumented one: handle that risk at design time, don't
   discover it by breaking a consumer later.
2. Internal/technical fields never exposed "because it's handy": only what is a genuine public
   contract is.

### 3. Extension rather than breakage: the "One-Version Rule"
1. Extend the existing contract with **optional fields** rather than forking a new version for a
   minor change.
2. A genuinely incompatible change (removing a field, changing a type) goes through
   `deprecation-migration` (Expand/Contract or explicit versioning), never through a silent
   modification of the existing contract.
3. Pagination, sorting, filtering: consistent conventions across the whole API, not reinvented
   endpoint by endpoint.

## Output / checkpoint
Final verification checklist cleared before shipping the contract: pagination consistent with the
rest of the API, backwards compatibility verified (no existing field removed/retyped), error
format compliant with the system-wide standard, no internal field exposed without reason.

## Guardrails
No over-engineering of the contract for a hypothetical need nobody asked for: the contract covers
the real need, extensible later if required, not pre-generalised. An incompatible change never
slips quietly into a "minor" evolution: go explicitly through `deprecation-migration`.

## Origin
Rewrite of the `api-and-interface-design` skill from a market generalist dev skill catalogue;
Hyrum's law, the "One-Version Rule" and the final verification checklist are taken as-is,
rewritten to the mentis template.
