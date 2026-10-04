---
name: runtime-prepare
description: Inspect and provision a reproducible financial-report runtime when required calculation, workbook, rendering or retrieval capability is absent.
---

Read the bound runtime recipe and the actual capability demand. Use the host's bundled dependency discovery first. Run the native environment probe and preserve its machine manifest. If a missing capability requires a build, use a fresh provisional environment directory and pinned dependencies; verify real output before assigning report work to it. Record dependency hashes, permissions, actual commands and failures.

Do not collect company data during environment setup. An exclusion from the report clock is allowed only when all report work is waiting solely for that setup. A reusable environment requires its own smoke/regression tests and promotion evidence. Return `environment_manifest`, `smoke_results`, and an explicit `provisional_components` list; no successful setup can certify financial correctness.
