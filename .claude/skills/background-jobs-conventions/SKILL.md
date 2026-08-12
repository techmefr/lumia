---
name: background-jobs-conventions
description: Use when writing or changing anything that runs outside the request cycle (queued job, worker, scheduled task, message consumer), the rules that keep async work from failing silently. Complements observability-instrumentation (what to log) and api-design (contracts) on the surface where nobody is watching when it breaks.
---

# background-jobs-conventions

Step 6 of the pipeline (`WORKFLOW.md`), for work that happens after the response has been sent.
The defining property of a background job is that **no user is watching when it fails**: there's no
red screen, no failed request, no one to report it. Every rule here exists because of that.

## When
As soon as a diff adds or changes: a queued job, a worker, a scheduled/cron task, a message
consumer, or a retry policy. Also when moving existing work *out* of the request cycle, which is
where most of these problems get introduced at once.

## Steps

### 1. Assume it runs more than once
1. **A job will be delivered twice.** Retries, a worker dying mid-run and the message returning to
   the queue, a deploy interrupting it: at-least-once is the normal case, not the pathological one.
   So a job either produces the same result when re-run, or it carries a guard that makes the second
   run a no-op.
2. **Make idempotency explicit, not incidental.** Key the effect on something stable (the entity id
   plus the intended transition), check-then-act inside a transaction, or record that the effect
   already happened. "It'll probably be fine" means charging a card twice.
3. **Pass identifiers, not objects.** Serialise the id and re-read the record inside the job. A
   snapshot serialised at dispatch time is already stale when the job runs, and it silently
   overwrites whatever changed in between.

### 2. Failure is a designed path
1. **Bound the retries** and back off between them. Unbounded immediate retries against a failing
   dependency turn one incident into two: the original failure plus the load you added to it.
2. **Distinguish retryable from terminal.** A timeout deserves a retry; a validation error or a
   missing record does not, and retrying it 25 times just delays the moment anyone finds out.
3. **A dead-letter destination is mandatory**, and so is someone looking at it. A dead-letter queue
   nobody reads is a folder where failures go to be forgotten, which is strictly worse than crashing
   loudly.
4. **Log the failure with the job's identity** (job name, the id it was handling, the attempt
   number). "Job failed" with no subject is not actionable at 2am.
5. Never swallow the error to keep the worker alive: a job that catches everything and returns
   normally reports success for work that didn't happen.

### 3. Ordering, timing and concurrency
1. **Don't assume order.** Two jobs dispatched in sequence can run in either order, or at the same
   time, on different workers. If a step depends on another having finished, express that with
   chaining or a state check, not with dispatch order.
2. **Guard against overlap** for anything that isn't safe to run twice concurrently (a scheduled
   aggregation, a sync): a lock with a timeout, so a crashed run doesn't hold it forever.
3. A **scheduled task that takes longer than its interval** will overlap with itself. Either bound
   the runtime or make overlap impossible.
4. **Keep a job's unit of work small enough to finish**: a job that processes an unbounded
   collection will eventually hit a timeout and be retried from the start, forever. Page it, or
   split it into one job per item.

### 4. Deploys and schema changes
1. **In-flight jobs run the old code against the new database, or the new code against the old
   payload.** A change to a job's payload shape has to be backwards compatible for at least one
   deploy, exactly like an API contract: add fields, don't rename or remove.
2. A job removed from the codebase whose messages are still queued will fail to deserialise: drain
   or migrate before deleting.

### 5. Verification
1. Run the job **twice** on the same input and confirm the second run is harmless. This is the one
   test that gets skipped and the one that catches the expensive bug.
2. Force a failure (make the dependency error) and confirm: it retries the number of times you
   intended, it lands in the dead-letter destination, and the log names the job and the id.
3. For anything scheduled, confirm the overlap guard by running it while it's already running.

## Output / checkpoint
The double-run and the forced-failure path were **observed**, with the evidence attached, not
reasoned about. A job reaching `gate` with only its happy path exercised isn't verified.

## Guardrails
- Never make a job idempotent "later": it's a design property, and retrofitting it means auditing
  every effect it has already had.
- Never point a retry at a shared external service without back-off; you can turn a partial outage
  into a full one.
- Draining, replaying or purging a queue in a shared environment is a **human decision**. Replaying
  a dead-letter queue re-executes real side effects.
- Broker/infra configuration (topics, partitions, worker counts, hosting) is infra reality and stays
  outside this repo.

## Origin
Gap found while scouting a market per-technology agent catalogue: it carried separate `kafka`,
`rabbitmq`, `bullmq`, `sidekiq` and `celery` agents while this framework had no block at all on work
running outside the request cycle, even though the Laravel backend uses queues. The per-broker agents
were not copied (per-library fragmentation, against our per-role doctrine); what's kept is the
broker-independent discipline. At-least-once delivery, idempotency keys, bounded retries with
back-off and dead-letter handling are established distributed-systems practice rather than anyone's
proprietary idea; the deploy/payload-compatibility section reuses the reasoning already in
`api-design` and `deprecation-migration`.
