# Native valuation environment

This is a build and verification recipe, not a claim that tools are currently installed. Resolve interpreter paths through the host's workspace-dependency discovery tool. Probe core Python (`jsonschema`, `yaml`), artifact Python (`openpyxl==3.1.5`), Node/Playwright, LibreOffice and PDF image rendering. Core and artifact Python may be different declared interpreters; preserve both in the environment manifest.

Run `scripts/prepare.py --out <fresh-state-directory>` under a suitable Python. It records executable/library versions and smoke output. `--build` explicitly provisions a venv using the bundled pinned requirements when the existing interpreter lacks them. This may require network and host approval; retain an actual failure rather than claiming setup succeeded. It never installs Docker or a vector database speculatively.

Use the package's `adapters/valuation/build.py` for actual calculation/export. A successful Python formula evaluation does not prove spreadsheet recalculation. Exercise the real selected spreadsheet engine's recalculate/save/reopen and input mutation route. Render the actual report and inspect each resulting page. Keep the environment provisional until tested evidence supports promotion.
