# Development summary

Standalone `python -m pr.esg prepare|build|check` supports the authored
`esg-learning-report/1` contract, 20–30 A4 pages, editable JSON/Markdown,
deterministic HTML/SVG, Playwright PDF, portable NanumGothic and relative PDF
source links. Multiple metrics share a compact year comparison table; claim
citations display IDs/pages without repeating full claim texts.

Checks bind input bytes, canonical content, adapter and all required artifacts
to fresh SHA-256; validate original/copy hashes, physical source pages, nonblank
A4 PDF pages, all print-sheet screenshots and overflow geometry. Null is
unavailable. HTML-only/prepared/failed rendering cannot certify PDF success.

42 network-free tests pass with the parent's isolated pypdf 6.19.0 environment.
Playwright 1.62.1/Chrome produced a synthetic 27-page PDF, 27 screenshots and zero
overflow. Intentional overflow fails with no success manifest. This is development
and self-verification; independent review and real SK hynix report acceptance
are not performed. Commands/results and changed paths are in
`output/esg-sk-hynix-20261004/reviews/adapter-development.md`.
