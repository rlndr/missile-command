---
name: factory
description: Run the software factory — take a feature through spec, build, four parallel reviews, and approval, then merge to main. Use for /factory <feature>, /factory next, /factory approve <job-id>, /factory rework <job-id> <note>.
argument-hint: <feature> | next | approve <job-id> | rework <job-id> <note>
disable-model-invocation: true
---

# Factory orchestrator

You are the orchestrator. You run the loop below, spawn every agent, and you are the
**only writer of `factory/board.json`**. You do not write code, specs, reviews, or
decisions yourself — agents do, each into its own file.

## The loop (edit this to change the factory)

```
                   ┌──────────────────┐
                   │     feature      │
                   └─────────┬────────┘
                             ▼
                   ┌──────────────────┐
                   │   spec-writer    │
                   │       opus       │
                   └─────────┬────────┘
                             ▼
                   ┌──────────────────┐
                   │     builder      │◄────────────────────┐
                   │       opus       │                     │
                   └─────────┬────────┘                     │
        ┌─────────────┬──────┴──────┬─────────────┐         │
        ▼             ▼             ▼             ▼         │
  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │
  │  security │ │     ux    │ │ ui design │ │    code   │   │
  │    opus   │ │   sonnet  │ │   sonnet  │ │   sonnet  │   │
  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘   │
        └─────────────┴──────┬──────┴─────────────┘         │
                             ▼                              │
                   ┌──────────────────┐   any CHANGES:      │
                   │   WAIT FOR ALL   ├─────────────────────┘
                   │   4 reviews in   │   resume builder
                   └─────────┬────────┘   (max 2 rounds)
                             ▼ all PASS
                   ┌──────────────────┐
                   │     approver     │
                   │       opus       │
                   └─┬───────────────┬┘
             APPROVE │               │ ESCALATE
                     ▼               ▼
              ┌─────────────┐ ┌─────────────┐
              │merge to main│ │ needs-human │ ◄── /factory approve
              └─────────────┘ └─────────────┘
```

Agents (in `.claude/agents/`): `spec-writer`, `builder`, `security-reviewer`,
`ux-reviewer`, `ui-reviewer`, `code-reviewer`, `approver`.
Reviewer → file: security → `review-security.md`, ux → `review-ux.md`,
ui → `review-ui.md`, code → `review-code.md`.

`MAX_REWORK = 2` — the builder is resumed at most twice by reviewers. If round 3 still
has a CHANGES, the job goes to `needs-human` without calling the approver.

## Paths

- `REPO` = `git rev-parse --show-toplevel` (the main checkout, stays on `main`)
- Job id: `NNN-slug` — next 3-digit number after the highest in board.json, plus a
  2–4 word kebab slug of the feature. Example `003-rate-limiting`.
- `JOB` = `REPO/factory/jobs/<job-id>/` — all markdown for the job lives here, on main's
  checkout, never on the feature branch.
- `WT` = `REPO/.worktrees/<job-id>` — git worktree on branch `factory/<job-id>`. The
  builder edits and commits here; reviewers read the code here.

Always pass agents **absolute paths**. Agents get their context from files, not from
this conversation — keep spawn prompts to paths and the round number.

## board.json

Read it, change it, write the whole file back (2-space JSON) after **every** state
change below, so the dashboard moves in real time. Shape:

```json
{ "jobs": [ {
  "id": "003-rate-limiting", "title": "Rate limiting", "branch": "factory/003-rate-limiting",
  "stage": "review", "round": 2,
  "reviews": { "security": "CHANGES", "ux": "PASS", "ui": "pending", "code": "PASS" },
  "history": [ { "security": "CHANGES", "ux": "PASS", "ui": "CHANGES", "code": "PASS" } ],
  "builder": "builder-003-rate-limiting", "note": "", "updated": "2026-11-02T10:00:00Z"
} ] }
```

- `stage` ∈ `spec` · `build` · `review` · `approve` · `needs-human` · `merged`
- `reviews` is the current round; `history` holds earlier rounds' verdict maps in order.
- `note` is one line shown on the card (why it's waiting, why it escalated).
- `updated` from `date -u +%Y-%m-%dT%H:%M:%SZ`.

## Preflight (every command)

1. `git -C REPO rev-parse --verify -q main` must succeed. If `main` has no commits, stop
   and tell the user to make an initial commit — the builder branches from it.
2. If `git status --porcelain` shows changes outside `factory/` and `.claude/`, warn the
   user that the builder won't see uncommitted work, then continue.

## /factory <feature>

1. **Create the job.** Pick the id, `mkdir -p JOB`, add the job to board.json with
   `stage: "spec"`, `round: 0`, `reviews: {}`, `history: []`.
2. **Spec.** Spawn `spec-writer` with: the feature text, `JOB`, `REPO`. When it finishes,
   check `JOB/spec.md` exists; copy its H1 (minus the id) into the job `title`.
3. **Build round 1.** `git -C REPO worktree add .worktrees/<job-id> -b factory/<job-id> main`.
   Set `stage: "build"`, `round: 1`. Spawn `builder` with **name `builder-<job-id>`**
   (if your Agent tool has no name field, store the returned agent id in `builder`
   instead), prompt: `JOB`, `WT`, `round 1`.
   When it returns, read the first line of `JOB/build.md`. `STATUS: BLOCKED` →
   go to **needs-human** with that reason.
4. **Review round N.** `mkdir -p JOB/round-N`. Set `stage: "review"` and
   `reviews` to all four `"pending"`. Spawn all four reviewers **in one message** (they
   run in parallel), each with prompt: `JOB`, `WT`, `round N`.
   As each one finishes, read the first line of its file and write its verdict into
   board.json immediately.
5. **WAIT FOR ALL.** The round is done only when all four `review-*.md` files exist in
   `JOB/round-N/` (check with `ls`, not with agent notifications). If a reviewer finished
   without writing its file, spawn it again for the same round. Never message the
   builder while any review is missing.
6. **Gate.**
   - Any `VERDICT: CHANGES` and `N ≤ MAX_REWORK` → push `reviews` onto `history`,
     `round: N+1`, `stage: "build"`, then resume the same builder:
     `SendMessage to builder-<job-id>`: "Round N reviews are in JOB/round-N/. Address
     every CHANGES finding, commit, and add a Round N+1 section to build.md."
     (If the builder can't be reached — e.g. a new session — spawn a fresh `builder` with
     the same name and tell it to read spec.md, build.md and every round folder first.)
     Then go to step 4 with N+1.
   - Any CHANGES and `N > MAX_REWORK` → **needs-human**, note "still CHANGES after round N".
   - All PASS → step 7.
7. **Approve.** Set `stage: "approve"`. Spawn `approver` with `JOB`, `WT`, `round N`.
   Read the first line of `JOB/decision.md`:
   - `APPROVE` → **merge**.
   - `ESCALATE` → **needs-human** with the decision's one-line reason.

**merge** — from `REPO` (on `main`):
`git merge --no-ff factory/<job-id> -m "factory: <job-id> <title>"`.
If it fails, `git merge --abort` and go to **needs-human** with "merge conflict".
On success: `git worktree remove .worktrees/<job-id>`, set `stage: "merged"`, and tell
the user the merge commit hash. Keep the branch.

**needs-human** — set `stage: "needs-human"` and `note`, then stop and tell the user why,
with the two ways forward: `/factory approve <job-id>` or `/factory rework <job-id> <note>`.

## /factory next

Find the first `- [ ]` line in `factory/backlog.md`. None → say the backlog is empty.
Otherwise mark it `- [x] … → <job-id>` and run `/factory <that text>`.

## /factory approve <job-id>

The human is the approver here. The job must be in `needs-human`. Run **merge** (step
above). Do not spawn the approver.

## /factory rework <job-id> <note>

1. Let N = the job's current `round`. Write the human's note to
   `JOB/round-N/review-human.md` starting with `VERDICT: CHANGES` (this is the one review
   file you write).
2. Add `"human": "CHANGES"` to `reviews`, push `reviews` onto `history`, set
   `round: N+1`, `stage: "build"`, clear `note`. The rework budget resets: treat N+1 as a
   fresh round 1 for `MAX_REWORK`.
3. Recreate the worktree if it was removed
   (`git worktree add .worktrees/<job-id> factory/<job-id>`), resume the builder as in
   step 6, and continue the loop from step 4.

## Reporting

Keep the user informed in one line per transition (e.g. "003 round 1: security CHANGES,
ux PASS, ui PASS, code PASS → resuming builder"). The dashboard is at
`cd factory && python3 -m http.server 8000` → http://localhost:8000/dashboard.html.
