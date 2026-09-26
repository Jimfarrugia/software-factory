# Updating pinned upstream material

Vendored files are selected, unchanged snapshots. Factory behavior belongs
outside `vendor/` so updates remain reviewable.

## Matt Pocock skills

1. Clone `https://github.com/mattpocock/skills` at the desired commit.
2. Replace only the skill directories listed in `upstream-lock.json` and its
   vendored `LICENSE`.
3. Inspect additions or renamed dependencies referenced by each `SKILL.md`.
4. Update the commit and aggregate SHA-256 in `upstream-lock.json`.

## Ponytail

1. Clone `https://github.com/DietrichGebert/ponytail` at the desired commit.
2. Replace `vendor/ponytail/AGENTS.md` and `vendor/ponytail/LICENSE`.
3. Reconcile intentional policy wording in root `AGENTS.md`.
4. Update its commit and aggregate SHA-256.

Run `scripts/validate-template`, inspect the full vendor diff, and test skill
discovery with OpenCode. Never automate upgrades to an unreviewed latest commit.
