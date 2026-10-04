# Native generator workflow

## Establish content and provenance

Record the audience, actual decision, genre, language, requested formats and current domain-review status. Content analysis remains with the domain author. Freeze the ORIGINAL reviewed valuation HTML and the corresponding result JSON; verify that entity, information cutoff, periods, scenarios, units and review versions agree. A previously redesigned report is not the preparation source.

For a new substantial report, plan three complete outputs using the native `transaction`, `executive` and `editorial` profiles, checks/visual inspection, independent selection and delivery. For a small edit or explicit profile choice, use proportionate regeneration and review. Do not compare against rejected custom layouts or create additional invented profiles.

## Resolve portable tools

Resolve `skill_root` from the skill actually loaded. Discover Python, Node, PDF raster tools/libraries, Playwright and browser availability through the environment's dependency tool or executable/package metadata. Record actual versions and capabilities. Native runtime overrides include `REPORT_OUTFIT_NODE`, `REPORT_OUTFIT_PLAYWRIGHT` and `REPORT_OUTFIT_CHROME`; set them from discovered locations only when needed. Do not assume a developer's home directory, macOS Chrome or globally installed dependencies.

The intended bundle uses `scripts/build.py`, `prepare_report.py`, `full_report.py`, `html_dom.py`, `render.mjs`, `verify_report.py` and `ledger.py`, with native report-outfit assets such as `base.css`, the three profile CSS files, full-report pagination resources, artwork/wordmarks and licensed fonts. Confirm that these native helpers and assets have actually been bundled. During packaging, the workspace's `report-outfit/` can supply the same native generator; record the concrete script/assets hashes used. Do not fall back to a different presentation engine.

## Prepare and run the actual native generator

Inspect current helper help before execution. The native valuation command contract is:

```text
<python> <skill_root>/scripts/prepare_report.py --source <ORIGINAL-reviewed-valuation.html> --results <corresponding-reviewed-results.json> --out <currentinput.json>
<python> <skill_root>/scripts/build.py --mode report --template valuation --input <currentinput.json> --design transaction --out <fresh-A-dir>
<python> <skill_root>/scripts/build.py --mode report --template valuation --input <currentinput.json> --design executive --out <fresh-B-dir>
<python> <skill_root>/scripts/build.py --mode report --template valuation --input <currentinput.json> --design editorial --out <fresh-C-dir>
```

Placeholders are discovered paths, not literal commands. Pass explicit `--input` and `--out` for every build. The native default mode is `specimen`; it is not a full-report substitute. Omitting input can select packaged sample content; never use that fallback for a future engagement. Reusing an output directory can replace its files, so create a new directory for each candidate/revision.

`build.py` calls the native full-report path and renderer by default. If generation and rendering need separate ledger entries, its supported `--html-only` option generates HTML first, then run:

```text
<node> <skill_root>/scripts/render.mjs <fresh-A-dir> <fresh-B-dir> <fresh-C-dir>
<python> <skill_root>/scripts/verify_report.py --help
<python> <skill_root>/scripts/ledger.py --help
```

Use the verifier's actual advertised flags, not an assumed schema. Render outputs include `report.pdf`, `rendered.html` and layout/mobile checks; browser screenshots and PDF-derived page rasters have different evidential roles. Locate outputs through actual manifests. If PDF-page rasterization is a separate step, use the discovered PDF tool and bind its page-image manifest to the exact PDF hash. A browser-page screenshot alone is not a visual review of the PDF.

The preparation script is currently a concrete Samsung valuation adapter. It recognizes specific source markup and `cases` result paths, supplies Korean Samsung summary/units/status and produces new chart definitions. Use it only for matching current reviewed inputs. For another issuer or domain, supply a current native input with domain-authored overview fields and generic `report_sections`, or have the authorized mapper owner implement the needed mapping. Inspect all generated overview claims; retention of body text alone cannot establish that summary text belongs to the new entity. See [content-contract.md](content-contract.md).

## Verify and independently select three full reports

1. Freeze current source/model/input hashes and a plan before generation. Log preparation/build/render/check operations when they occur, including failures. Record the actual native script, profile, template, mode and asset versions.
2. Generate all three complete native reports from the same frozen input. `full_report.py` uses the actual `build.py` `DESIGNS`, `art`, `pages`, `table`, `chart` and related constructors. Keep all supplied sections, qualifications and evidence; allow block/table-row continuation instead of forcing the old specimen page count.
3. Verify input retention/provenance and complete output coverage. Compare metric bindings, paragraph/cell multiplicities, table values and newly generated charts with their reviewed result paths. Check generated overview pages as well as retained sections. Inspect sources/links, conditional wording, native concept-status labels, overflow and every actual PDF page. Passing layout bounds does not establish completeness or economics.
4. Freeze the three full candidate PDFs, rendered HTML, actual PDF-page images and check manifests. Give an independent reviewer opaque labels and the same current content/model-review basis, without an author preference or an old-design comparison. Dispatch [the scoring prompt](design-judgment.md) at the highest capable available model/effort. `gpt-6-astra`/`ultra` is suitable only when the environment actually exposes and supports it. Capture actual requested and observed metadata; absence of the channel means selection remains provisional.
5. Select among eligible native candidates only. Preserve blind scorecards before revealing A/B/C identities. Fix concrete observed presentation/retention defects within the authorized scope, create new artifact hashes and obtain corresponding review coverage. If no candidate is eligible, return the blockers rather than accepting by deadline or average score.

## Record and hand over

Use the ledger's supported `start`, `finish`, `select` and `graphs` commands/schema. Plan preparation, the three native builds, render/retention checks, independent selection and final handover. A failed operation remains a failed event; generated graphs must distinguish plans from observed work. Inspect generated evidence links before claiming they are clickable; provide a companion evidence index when the graph exposes only record anchors/path text.

Record or attach a hash-bound review sidecar containing:

- Source HTML/model JSON/input provenance; actual generator/helper/assets hashes; native profile, template, `mode=report` and output directory.
- Generated/rendered HTML, PDF, each inspected PDF-page image and retention/layout/check hashes, with exact page coverage.
- Reviewer identity/independence, disqualifiers, rubric scores, selection rationale and open findings.
- Requested model/effort and actual invocation parameters; observed model/effort from returned metadata, their evidence source and response/run ID where available. Unknown observed fields remain `unknown`; a request is not proof of execution. Record capability fallback honestly.
- The supplied financial/domain review paths/hashes and conditional status. Design review does not supersede financial lifecycle gates.

Preserve prior reviews and create a new record when content, charts, pagination or output bytes change. Transfer unchanged inspection scope only with demonstrated artifact identity and an explicit statement. Deliver the selected native report in the requested supported formats, the three-candidate selection basis, retained checks and replay details. Native branding remains a concept application, not a Deloitte-issued financial opinion.
