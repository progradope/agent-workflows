---
name: qa-verify
description: Prove a change works on a running system and write an evidence packet, so the human reviewer does not have to re-test it locally. Use after automated tests pass and before independent review or publication.
---

# QA verify

Automated tests prove units and wiring. This stage proves the **behaviour a
user or operator would see**, on a running stack, and records evidence a
reviewer can check in minutes instead of reproducing the change locally.

The target outcome is an evidence packet whose "Manual checks required"
section is empty. Anything left there must be genuinely impossible to
automate here, with a reason and exact steps.

Project instructions own how the stack starts, which environments are
allowed, and which checks are mandatory. This skill adds behavioural
verification on top; it never replaces or weakens a project gate.

## Rules

- Verify against the running system, not by reading code. "The code looks
  correct" is not evidence.
- Never point at shared, staging, or production environments or real customer
  data unless project instructions explicitly allow it. Use local containers
  and seeded test data.
- Record real commands and real outputs. Do not paraphrase a result you did not
  observe. If something could not run, say so and why.
- If the stack cannot start, record a blocker with the error. Do not mark
  behaviour verified from unit tests alone.
- Keep secrets, tokens, and personal data out of evidence (redact headers,
  tokens, emails).
- Re-run this stage after any consequential code change; old evidence does not
  cover a new diff.

## Choose where to run

There are two targets. Both are run by an agent; the user only reviews evidence.

- **vps** (default): the machine the coding agents run on. Use it when the
  change can be proven with the repo's tests, stubs, and small containers.
- **mac**: the user's own machine with the full local stack (heavy services
  such as camera orchestrators or Frigate). Use it when a matrix row needs a
  service that cannot run or be faithfully stubbed on the VPS.

The user can name the target ("target mac"). Otherwise use vps, and when the
change touches parts that need the full local stack, say so in the plan's
Proof line and ask which target to use. Never silently downgrade: if the chosen
target is unreachable, report it as a blocker.

Project specifics, including how to hand work to the mac target, are in the
project's notes file when one exists:
- drones_columbus: [references/drones-columbus.md](references/drones-columbus.md)

## Ordered workflow

### 1. Map the change to observable surfaces

From the approved plan and the current diff, list what a person or system can
observe changing:
- UI routes/views and the user roles that reach them
- HTTP endpoints (method, path, status codes, payload shape)
- health/actuator endpoints, scheduled jobs, sync tasks, queues
- database migrations and the data they touch
- configuration and environment variables (new, renamed, defaults)
- emails, notifications, files, exports

Also list surfaces the diff touches **unintentionally** (shared modules,
common code, renamed fields). Each needs at least a regression check.

### 2. Build the verification matrix

One row per acceptance criterion, plus the edge cases that apply:
- boundaries (exactly at the threshold, one below, one above)
- missing, empty, and malformed input or configuration; the default value
- permissions: allowed role, denied role, unauthenticated
- state transitions: create, update, delete, retry, expiry, cancellation
- time: time zones, UTC vs local, date boundaries, clock-dependent logic
- dependency failure: upstream timeout/error, sync that fails or stalls, and
  whether a cached/saved result goes stale and misreports health
- migrations on existing data, not only an empty database
- regression: the exact scenario from the original issue

### 3. Bring up the stack

Use the project's notes for the chosen target, then the project's documented
way (its verify skill, README, compose files, Gradle/Maven tasks,
Testcontainers). Seed the minimum data the matrix needs.
Record the commands and confirm the app is healthy before testing.

### 4. Exercise each row

- **API/health:** call the endpoint and record request and response
  (status + relevant body). Cover success and failure rows.
- **UI:** use the project's Playwright setup. Run the existing E2E tests for
  affected flows. For a user-visible change or bug fix, add or extend an E2E
  test in the project's conventions so the check is repeatable in CI. Capture a
  screenshot of the key state and keep the Playwright trace for failures.
- **Jobs/sync:** trigger the job (or run it via test hooks), then observe the
  resulting state, logs, and health output.
- **Migrations:** apply to a database with representative existing rows;
  confirm the app boots and affected reads/writes work.
- **Config:** start once with the new variable set, once unset (default), and
  once with an invalid value where relevant.

### 5. Prove the fix (bugs)

Where practical, show the original failure on the base commit and the passing
behaviour on the task head, using the same steps. If reproducing on base is
impractical, say why.

### 6. Write the evidence packet

Write `qa-evidence.md` in the task directory beside the checkpoint (use the
deliver helper's `path` command), unless the project mandates another place.
Keep screenshots and traces beside it. Summarise the packet in the PR body or
review packet in the project's format; do not commit evidence files to the
application repository unless the project asks for that.

## Required output format

```markdown
# QA evidence: <task>

**Head:** <full sha>   **Target:** <vps / mac>   **Stack:** <how it was started>   **Data:** <seed used>

## Verdict
<one line: verified / verified with gaps / blocked>

## Matrix
| # | Criterion / edge case | How verified | Result | Evidence |
|---|-----------------------|--------------|--------|----------|
| 1 | ...                   | curl / Playwright / job run / migration | PASS/FAIL | file or snippet |

## Regression
<original scenario: before (base) vs after (head)>

## Unintended surfaces checked
<shared modules/flows touched and how they were checked>

## Tests added for CI
<new or extended E2E/integration tests that make these checks repeatable>

## Manual checks required
<empty if none. Otherwise: what, why it cannot be automated here, exact steps,
expected result. Keep each under 5 minutes.>

## Environment notes
<new/changed env vars, defaults, migrations to apply before deploy>
```

## Hand-off

Report the verdict and the packet path to the coordinator. A FAIL row returns
to implementation through the normal repair loop. A blocked stack is a blocker,
not a pass.
