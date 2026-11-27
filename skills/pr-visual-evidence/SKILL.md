---
name: pr-visual-evidence
description: Capture before/after screenshots (and short GIFs for interactions) of every user-visible change and show them inline in the pull request description. Use for any PR whose diff changes what a user sees, after the PR exists, including when asked to add evidence to an existing PR by number.
---

# PR visual evidence

Reviewers of a visual change should see it without checking out the branch.
For every PR that changes what a user sees, attach before/after evidence to the
PR automatically. This is required, not optional, for visual changes.

Uploads use GitHub CLI's `--attach` flag (gh v2.99.0 or later), the same
attachment storage as the "Attach files" button in the PR editor. The flow is
modelled on open-mercato/skills (MIT), operation `attach-image-evidence`.

## Which script

Use the repository's `scripts/attach-pr-evidence.sh` when the checkout has one.
Otherwise use the copy bundled with this skill, `scripts/attach-pr-evidence.sh`
in this skill's own folder. Both take the same arguments.

## When it applies

The diff changes something a user can see: frontend code, CSS, templates,
Vaadin views or layouts, user-visible copy, icons, or images. It does not apply
to backend-only, test-only, docs-only or CI-only changes; say "no visual change"
and leave the PR description alone.

## Existing PR (invoked with a PR number)

When asked to add evidence to an existing PR, for example
`$pr-visual-evidence 2422`:

1. Read the PR with `gh pr view <n> --json number,title,state,headRefName,headRefOid,baseRefName,files,body`.
   Skip it if it is closed or merged, or if no changed file is user-visible
   (see "When it applies"); report "skipped: <reason>" and stop.
2. If the description already has a Visual evidence section for the current
   head SHA, report "already up to date" and stop.
3. Work in a separate worktree for the PR head (reuse the PR's own thread
   worktree if this is that thread). Never switch the branch of a main
   checkout. Build the base branch in a second worktree for the before shots.
4. Read the ticket and the diff to decide the screens and states, then follow
   Capture and Publish below.
5. Stop only what you started (app processes, containers). Remove the two
   temporary worktrees when done.
6. This skill only edits the PR description. It never pushes, commits, merges
   or changes the PR's code.

## Capture

1. List the affected screens and states from the diff and the ticket (page,
   role, data state, open dialogs, error and empty states).
2. Choose widths that matter for the change. Default: 360, 400, 800 and 1280 px.
   A width-specific fix also includes the widths on both sides of its
   breakpoint.
3. Reuse screenshots the verification step already took (for example
   qa-verify's evidence `screenshots/` folder) when they match the current head.
   Otherwise capture them with the repo's Playwright setup against a locally
   running app with seeded test data. Follow the machine notes (qa-verify's
   references) for how to start the app on this machine.
4. Capture **before** on the base branch (usually `origin/dev`) and **after** on
   the PR head, with the same steps, data and widths.
5. For interaction or animation fixes (spinners, hover, drag, double-click),
   also record a short clip of the after state (at most 10 s) and convert it to
   a GIF under 8 MiB with ffmpeg, so it plays inline.
6. Name files `before-<screen>-<width>.png` and `after-<screen>-<width>.png`
   (and `after-<screen>-<interaction>.gif`).
7. Look at every image before publishing. Recapture blank pages, loading
   spinners that are not the point of the fix, error pages and cut-off views.

Safety: test data only. Never capture tokens, API keys, real people's emails,
names or locations, or other secrets. Crop or skip a screenshot that would show
one, and say so.

## Publish

After the PR exists and its head contains the change:

1. Check `gh --version` is 2.99.0 or later; if not, stop and say so.
2. Write a short body file: what changed visually, then a table of screen,
   width, before and after file names, plus any states you could not capture
   and why.
3. Run the script (see "Which script"):
   `attach-pr-evidence.sh --pr <number> --body <body.md> <files...>`
   Run it once with `--dry-run` first. Order files before/after per screen.
4. The script uploads each file with `gh pr edit --attach` and writes a
   **Visual evidence** section into the PR description between
   `<!-- pr-visual-evidence:start -->` and `<!-- pr-visual-evidence:end -->`.
   Re-runs replace that section and keep the rest of the description. Nothing
   is pushed to any branch. (`--in comment` posts one PR comment instead.)
5. Whatever later rewrites the PR description (the create-pr wrapper, body
   templates, review packets) must keep the marked section unchanged. If the
   repo has a PR-body check, run it after the update.
6. After new commits change the visuals, re-run it so the section shows the
   current head (it records the head SHA).
7. Report the PR URL, the files attached, and anything you could not capture.

Attachment links can be opened by anyone who has the link, even for a private
repository, so the test-data-only rule above is strict.

## Never

- Attach evidence from a different head than the PR's current one.
- Commit evidence files to any branch.
- Drop or rewrite the marked evidence section when updating the description.
- Report a visual change as verified when the after screenshot was not
  captured. State what is missing instead.
