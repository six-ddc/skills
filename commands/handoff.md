---
description: Write the session's task state, key decisions, background constraints, and next steps into a self-contained handoff document in the project directory, so a fresh session or agent can read it and seamlessly continue the work — development, debugging, or review
argument-hint: [optional: focus scope (e.g. "review findings only") or an output path]
---

# Handoff — Session Handoff Document

Write everything worth carrying forward from this session into a Markdown document. The reader is a **fresh session or agent that cannot see any of this conversation** — after reading the document, it must be able to pick up the work directly, without asking again.

$ARGUMENTS

## Location and naming

- Default to the current working directory — do not create any directory; if the arguments specify a path, that wins.
- Filename: `handoff-YYYY-MM-DD-<slug>.md`. Get the date from `date +%F` — never from memory. The slug is a lowercase kebab-case English topic, specific enough to distinguish tasks (`payment-refund-race-fix`, not `bugfix`).
- If the file already exists: read it first. Same task continuing → update the file in place, stating only the latest state — no revision narration ("compared to last time", "previously done"); different task → append `-HHMM` to the filename.

## Information source: this conversation only

The document is a persisted distillation of the current session context — like a compact that survives to disk. Writing it is not a new task:

- **No investigation.** Do not read files, re-run tests, or explore code to fill gaps in the document. Information the session doesn't contain is written as "not covered in this session", not looked up.
- **Two cheap exceptions**, both for the header only: `date +%F` for the filename, and one `git log --oneline -3 && git status --porcelain` snapshot for the branch/HEAD line — a stale hash written from memory misleads the successor.
- **Verification status comes from the session record.** For every test / lint / build actually run this session, report the **latest** result seen; anything not run is "not verified" — never "should be fine", and never re-run now to upgrade it.

## Document structure

A skeleton — trim to what actually exists. Delete empty sections entirely; never pad.

```markdown
# Handoff: <task title>

> Date: <YYYY-MM-DD> | Branch: <branch> | HEAD: <short-hash> | Working tree: <clean / N files uncommitted>

## Task and goal
What is being done, the user's original request, and what counts as done (acceptance criteria).

## Current progress
- **Done**: each item with file:line or commit hash, plus verification status (tests passing / not verified)
- **In progress**: how far it got, where it stopped, and the next concrete action
- **Not started**: remaining scope

## Key decisions
Each entry has three parts: the decision, the rationale, and the alternatives rejected and why. For genuine trade-offs, keep the full shape: what was weighed against what, which constraint tipped it, and what would have to change for the rejected option to win. Mark decisions the user explicitly made as "(user decision)" — the successor must not overturn them unilaterally.

## Approaches: proven and ruled out
- **Worked**: approaches and techniques verified in this session and worth reusing (with where they were applied)
- **Ruled out**: what was tried and why it failed, each with the concrete evidence (error message, failing output) — "didn't work" without the why gets retried anyway. Note conditions under which a ruled-out option would be worth revisiting.

## Background and constraints
What the successor cannot learn from the code or git history: business context, external dependencies, corrections and preferences the user gave during the session.

## Next steps
A priority-ordered action list. Each item carries what's needed to start immediately (file paths, commands, expected outcome).

## Key references
Core file paths, related tickets / MRs / wiki links, common commands (how to run tests, start the environment, reproduce the problem).
```

## Writing discipline

- **Self-contained**: no "as mentioned above", "the file we discussed", or any reference that requires the conversation — replace every one with a concrete path, commit hash, or absolute date. Reread the finished document: any passage that needs the conversation to make sense is a defect.
- **Pointers over pasting**: locate code with file:line and commit hashes, don't transplant blocks; inline only short, decision-critical fragments (error messages, key diffs).
- **Report faithfully**: failing tests get the failure reason and an output excerpt; skipped steps are stated as skipped; nothing unverified gets dressed up as done.
- **Record in-session corrections**: approaches the user corrected and preferences they stated are exactly what a fresh agent will get wrong again — give each its own entry under "Background and constraints".
- **Select ruthlessly — but compress narrative, not decisions**: the test for every line is "does this change the successor's next action?" — if not, cut it. The goal is the shortest document that sustains the work, not a session log. Cutting applies to process narrative (what was tried in what order, tool-call play-by-play); it never applies to decision substance — trade-off rationale, rejected alternatives, constraint details, and exact parameter/threshold values survive at full fidelity, because they are precisely what the successor cannot reconstruct.

## Wrap-up

After writing, report the file path to the user and provide a one-line resume prompt they can paste into a new session, e.g.:

> Read `handoff-2026-07-17-payment-refund-race-fix.md` first, then continue with item 1 under "Next steps".
