---
name: short-reverse-dcf
description: Run the existing frozen Hyundai reverse-DCF diagnostic in a fresh operational session with real independent review and explicit whole-path usage. Use for the bounded short-session experiment, not a new valuation report or live market-price opinion.
---

Use the source-development helper at `../../development/hyundai-reverse-dcf/short-session-001/runtime.py`. Resolve it relative to this skill. Preserve the existing reference contract, model, twelve checks and review criteria.

Prepare a new attempt directory with `python3 runtime.py prepare <absolute-new-directory>`. Pass only that attempt's `handoff.txt` to one fresh native main-role worker with `fork_context=false`, inherited model and requested `high` reasoning. Save its actual spawn receipt as `coordinator-spawn.json` before allowing final integration. The operational worker executes the supplied code and delegates a fresh independent reviewer; it delivers `RESULTS.md` itself. If descendant delegation is unavailable, keep the attempt incomplete rather than using a fabricated review or a user-facing chat.

Preserve actual spawn, completion and close receipts. Observe coordinator, reviewer, errors/retries and the real parent dispatch/coordination usage. Separate package development from operational costs, but do not omit operational parent work. The exploratory limits are 500,000 input tokens and 300 seconds; unknown usage cannot prove a pass. Measure one pilot before three fresh repetitions. Do not activate a release or generalize this fixed-input diagnostic to full reports.
