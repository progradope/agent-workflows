---
name: fix-ticket
description: Fix one GitHub issue end to end with deliver and qa-verify under Shivam's ticket rules (read ticket, confirm still valid, minimal scoped fix, regression test, evidence, sign-off before any push). Use when given an issue number or URL to fix.
---

# Fix ticket

Input: an issue number or URL. The repo is SkyTradeLinks/drones_columbus unless
another is given. Work in the current worktree, branched off dev.

Use deliver as the coordinator and qa-verify for verification. The rules below
add to deliver and the project's own rules; they never loosen a project gate.

## Modes

- **New ticket:** given an issue in a fresh worktree off dev. Run every step.
- **Takeover:** this worktree already has work for the ticket (an existing diff,
  or the user says "takeover"). Do not redo or rewrite it. Read the issue and
  the existing diff, confirm the ticket still applies, then start at step 3 and
  write the plan from them.
- **Continue:** a plan already exists and the user approves it, even in a few
  words ("approved", "ok, go"). Record the approval and continue from the first
  unfinished step. Apply any short answers the user gave to open decisions.

## Ground rules (these override anything older in this thread)

- Learn what this machine can do by checking, not from earlier messages. Before
  planning validation, run `java -version` and `docker info`, and read
  `~/.agents/skills/qa-verify/references/drones-columbus.md`. If earlier
  messages say a tool is missing and it is now present, use it and correct the
  plan.
- Never push, and never ask to push, before output sign-off. If a check needs
  the user's Mac, use qa-verify's mac target; it fetches the branch from the VPS
  over SSH.
- Do not use or suggest `run-fix`.
- Keep "Needs your decision" for real product or scope choices.

## 1. Read the ticket

Run `gh issue view <NUMBER> --repo SkyTradeLinks/drones_columbus --comments`.
Work only from what the ticket and its comments actually say, plus the code.
Summarise it in 2-3 lines.

## 2. Confirm it is still valid

Check current dev and reproduce the problem. Many tickets are old. If it is
already fixed, no longer applies, or cannot be reproduced: STOP. Report what you
checked and the evidence. Write no plan and change no code. Do not invent a
change.

## 3. Plan (gate 1)

Draft the plan through deliver and end with its plan review card. Include:
- the ticket summary and the reproduction evidence on dev
- the MINIMAL fix for exactly what the ticket asks
- under Out of scope: refactors, drive-by edits, and anything touching CI,
  build, migrations, or config
- if the ticket truly needs CI/build/migration/config changes, or is ambiguous,
  put it under Needs your decision instead of assuming

Wait for approval.

## 4. Implement and test

- Make the minimal fix only. Touch nothing outside what the ticket needs.
- Add or update a regression test that follows the repo's existing patterns
  (e2e or unit). It must fail on dev without the fix; show that where practical.
- If an e2e test needs MAPBOX_TOKEN and it is unset, say so explicitly. Never
  let a test skip silently and count it as passing.

## 5. Verify

Run the project's checks for real on this machine: formatter (Spotless),
compile, and the selected unit and e2e tests. Show each new regression test
failing on origin/dev and passing on the branch.

Then run qa-verify on a running stack, including screenshots of each affected
page in the running app at the widths the ticket cares about. Before starting the stack, check that no other
app stack is running on this machine and use a port unique to this worktree.
Capture before/after evidence (screenshots for UI, request/response for API).

## 6. Output sign-off (gate 2)

Stop at deliver's output review card. Nothing is pushed and no PR is opened
before the user signs off. The card, or the evidence packet it links, must
include:
- the ticket summary
- what changed and why
- exact commands to run and test it locally
- selectors and assumptions the user should confirm
- manual checks required, if any

After sign-off, deliver publishes the PR and maintains it until merged or closed.

## 6b. Visual evidence on the PR

If the change is visible to users, attach before/after evidence to the PR right
after it is published, and again after later commits change the visuals. Use
the project's PR visual evidence skill (for drones_columbus:
`pr-visual-evidence` with `scripts/attach-pr-evidence.sh`), passing the
qa-verify screenshots that match the current head. Put the evidence comment
link in the PR body and in the readiness report. If the project has no such
skill yet, list the screenshots in the PR body and tell the user.

## 7. After merge

When deliver records the merge, also give a short post-merge checklist: the
exact steps to re-test the fix on dev.
