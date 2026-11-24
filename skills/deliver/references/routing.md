# Skill routing

Read actual skill files before applying them. Resolve project skills first for
project-specific procedures, and personal skills for the general stages below.
Do not run every installed skill or repeat equivalent checks.

## Main stages

- Context: project workflow; ponytail and codeguard when supplied by the project.
- Analysis: personal audit and scope; architect for non-trivial design.
- Plan: project plan and its approval/amendment rules. Use spec-create only when
  a new durable contract is required.
- Implementation: personal develop, with project tdd and specialist guidance.
  A project implement skill may have a narrower contract (such as issue-based
  work); read it before choosing it instead of develop.
- Tests: personal test; project verify owns check selection and pre-commit gates.
  Personal check is a fallback when the project has no verification procedure.
- Behavioural verification: personal qa-verify after tests pass, on a running
  stack, producing the evidence packet for the output sign-off. Re-run it after
  consequential changes. It adds to project verify; it never replaces it.
- Docs and self-check: personal document as needed; project code-review and
  security-self-check as applicable.
- Simplification: ponytail-review after author checks and before independent
  review, repeated after substantive repairs. Use the project's version when
  supplied, otherwise the bundled version. Record findings and dispositions.
- Independent review: project adversarial-review, security-review, and
  e2e-impact-review at their policy thresholds. Preserve the original reports.
- Publication: project create-pr and its required publishing script.
- PR maintenance: personal autopilot for triage plus the T3 PR watcher, kept
  active after green CI until the PR is merged or closed.
- Diagnosis: project diagnosing-bugs and build-fix when applicable; personal
  debug is a fallback if supplied by the user.
- Readiness: personal finish, checked against the current head; keep watching.
- Final handoff: deliver records a confirmed merge/closure and stops the watch.

## Specialist routing

Use the project's guidance for the actual change:
- Spring/Java: springboot-patterns, springboot-security, springboot-tdd.
- Persistence/migrations: jpa-patterns, database-migrations.
- Interfaces/module boundaries: codebase-design.
- User copy: plain-language and the project's label catalog.
- Security ergonomics: sharp-edges.
- Related instances of an established bug: variant-analysis.
- Verify the author's suspected security finding: fp-check; never use it to
  dismiss an independent reviewer's finding.
- Agent assets: writing-for-agents and the project's agent-config check.
- Meaningful workflow/architecture context changes: sync when required.

## Missing capabilities

The bundle supplies audit, scope, architect, develop, test, qa-verify, document,
autopilot, finish, and ponytail-review. Existing local skills are preserved by the
installer; inspect the actual installed version before use.

Specialist and repository-policy skills remain in the project checkout; this
package does not copy them. If a required project skill is absent, inspect the
project's documented equivalent. If no valid equivalent exists, report the
missing prerequisite before claiming that gate passed.

Outside a project with its own review policy, obtain a fresh independent
correctness review before publishing substantive code, and a separate security
review for security-sensitive changes. Do not invent project tier names or
reviewer evidence.
