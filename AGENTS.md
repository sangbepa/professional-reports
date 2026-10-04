# professional-reports repository entrypoint

This repository prepares an immutable professional-reports development release for Codex. Read README.md and package/docs/package-status.md. Do not interpret installation or a synthetic smoke as report acceptance.

1. Run `python3 scripts/verify.py`. It verifies the active release's full member set and returns root/version/release_id. If absent, run `python3 scripts/setup.py --activate-development`, or `bash scripts/cloud-setup.sh` during a Linux cloud-environment setup requiring native PDF/XLSX tools. Setup installs only project-local Python/Node/state; do not substitute package/ source for an installed release.
2. Preserve that installed root for the task. Read its AGENTS.md and skills/professional-reports/SKILL.md, then load only selected version/hash-bound organization, personas, methods and runtime definitions. `python3 scripts/pr.py` runs its real CLI from the verified installed root. The wrapper supplies project-local browser paths dynamically; setup shell exports need not persist.
3. Confirm current host native subagent tools, lower host worker limit, required source services and supplied reasoning settings. Spawn actual workers with fork_context=false and record actual receipts. Never simulate independent reviewers or claim missing tools available.
4. Register actual request/cutoff before substantive research. Preserve the installed timing contract and protected quality criteria, including exact revised-artifact review/real spreadsheet recalculation/all first-report PDF-page coverage. No manufactured approval or deadline reset. An alternative baseline mandate needs a separately authorized contract; do not call it an old 600s success.
5. Use the bundled existing specimen. Keep all output, raw evidence, credentials, state and runtime outside package/. Never write API keys to files, console, prompts or Git. Check actual API access, not just presence of OPENDART_API_KEY.
6. Public edition excludes the registered company-specific frozen diagnostic files. If explicitly asked for that frozen-case route, inspect its registry and return capability insufficient rather than reusing a different company's data. General valuation starts with fresh originals.

Tests: `.runtime/python/bin/python -m unittest discover -s tests -v`. Portable mechanical smoke: `python3 scripts/smoke.py --out outputs/new-smoke`. Full synthetic native smoke: `python3 scripts/smoke.py --render --out outputs/new-native-smoke`. Do not recycle an output directory. These are not full professional report acceptance runs.

All four libraries remain provisional. Protected evaluator/criteria changes require human approval; public tests cannot be called blind holdouts. Preserve source/immutable release/installed active state separation. Updating the repository does not repin an in-progress run or update another user-global plugin cache.

The user explicitly authorized publication of the twelve protected evaluation/reviewer/approval files in docs/publication-scope.json. Their criteria remain protected against autonomous edits. Public disclosure does not approve a report or release and does not make public cases blind holdouts.
