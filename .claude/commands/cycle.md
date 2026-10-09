---
description: Orchestra cycle — architect → local coder → verify → Codex review → fix → commit.
---
Feature: $ARGUMENTS

Follow `.orchestra/ORCHESTRA.md` (open mode):
1. Architect the feature into `.orchestra/SPEC.md` (goal + per-task acceptance criteria). Show it and STOP for my approval (checkpoint 1).
2. On approval, per task: curate a minimal task and delegate to `.orchestra/scripts/code.py`; verify with the project's build/tests after each.
3. Run `.orchestra/scripts/review.sh` with the acceptance criteria. Apply findings via the coder (max 3 rounds); escalate if stuck.
4. Show the final diff and STOP for my approval before committing (checkpoint 2).
5. On approval, commit on a feature branch.
Never write feature code yourself except as a flagged last resort.
