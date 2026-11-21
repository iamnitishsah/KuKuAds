"""Render docs/DETAILED_WORKING_REPORT.md to styled HTML (and Edge prints it to PDF)."""
from pathlib import Path

import markdown

ROOT = Path(r"C:\Users\kunal\nitish\promo-finder")
MD = ROOT / "docs" / "DETAILED_WORKING_REPORT.md"
HTML = ROOT / "docs" / "DETAILED_WORKING_REPORT.html"

CSS = """
@page { size: A4; margin: 15mm 14mm 15mm 14mm; }
body { font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.5; color: #1f2328; max-width: 980px; margin: 0 auto; padding: 18px; }
h1 { font-size: 24pt; margin: 0 0 4px; letter-spacing: -0.4px; }
h2 { font-size: 15pt; margin-top: 26px; padding-bottom: 4px; border-bottom: 1px solid #d0d7de;
     page-break-after: avoid; }
h3 { font-size: 12pt; margin-top: 18px; page-break-after: avoid; }
p, li { orphans: 3; widows: 3; }
table { border-collapse: collapse; width: 100%; margin: 10px 0 14px; font-size: 8.8pt; }
th, td { border: 1px solid #d0d7de; padding: 4px 6px; vertical-align: top; text-align: left; }
th { background: #f6f8fa; }
tr { page-break-inside: avoid; }
code { font-family: Consolas, "Courier New", monospace; font-size: 0.88em;
       background: #f6f8fa; padding: 1px 3px; border-radius: 3px; }
pre { background: #f6f8fa; border: 1px solid #e5e7eb; border-radius: 5px; padding: 8px 10px;
      font-size: 8.2pt; line-height: 1.35; white-space: pre-wrap; word-break: break-word;
      page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: inherit; }
blockquote { border-left: 3px solid #d0d7de; color: #57606a; margin-left: 0; padding-left: 12px; }
hr { border: 0; border-top: 1px solid #d0d7de; margin: 22px 0; }
.cover { border-bottom: 2px solid #1f2328; padding-bottom: 10px; margin-bottom: 14px; }
.meta { color: #57606a; font-size: 9.5pt; }
a { color: #0969da; text-decoration: none; }
"""


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "toc"],
        output_format="html5",
    )
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Detailed Working Report - Promo Finder</title>
<style>{CSS}</style></head>
<body>
<div class="cover">
<h1>Detailed Working Report</h1>
<div class="meta">Promo Finder (Problem 1) &middot; archived full run <code>outputs/full-run</code>
&middot; 50 episodes &middot; generated from the real artifacts</div>
</div>
{body}
</body></html>"""
    HTML.write_text(html, encoding="utf-8")
    print(f"wrote {HTML} ({len(html):,} chars)")


if __name__ == "__main__":
    main()
