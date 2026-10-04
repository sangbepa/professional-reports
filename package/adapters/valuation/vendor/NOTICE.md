Native report-outfit files copied from the workspace report-outfit implementation.
The source tree did not include a general software license; this copy does not
assert a new license or grant third-party redistribution rights. Original font
licenses are included beside OpenSans.ttf and NanumGothic.ttf. Firm wordmarks and firm-facing default language were removed. The native
constructors and design profiles are retained with a neutral scenario header.
Reports explicitly state that financial review is unperformed.

Local changes:
- build.py and base/transaction CSS: neutral scenario branding, no firm marks;
  removed both original firm SVGs and replaced the default cover/footer text.
- build.py: an explicit chart type `bars` selects the existing generic native
  bar constructor, including for valuation overview pages. This handles signed
  and zero amounts; the old range constructor assumes strictly positive values.
- render.mjs: removed the sibling valuation-workbench fallback. Package/env and
  host runtime discovery remain available; no author-checkout path is needed.

No sample company inputs or old financial artifacts were copied. The adapter
invokes build.py with explicit current input, --mode report, --template valuation,
a selected native profile and a fresh output directory. Its full_report.py,
html_dom.py, fonts, CSS and pagination JS are retained locally.
