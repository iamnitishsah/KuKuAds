"""Render SOLUTION.md with a compact 2-page CSS to check the page count."""
from pathlib import Path

import markdown

ROOT = Path(r"C:\Users\kunal\nitish\promo-finder")
OUT = Path(r"C:\Users\kunal\AppData\Local\Temp\opencode\solution")
OUT.mkdir(parents=True, exist_ok=True)

CSS = """
@page { size: A4; margin: 11mm 12mm; }
body { font-family: -apple-system, "Segoe UI", Arial, sans-serif; font-size: 9.4pt;
       line-height: 1.38; color: #1f2328; }
h1 { font-size: 18pt; margin: 0 0 5px; letter-spacing: -0.3px; }
h2 { font-size: 11.5pt; margin: 12px 0 5px; padding-bottom: 2px; border-bottom: 1px solid #d0d7de; }
p { margin: 4px 0 6px; }
ul, ol { margin: 3px 0 6px; padding-left: 16px; }
li { margin: 1px 0; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 8px; font-size: 8.2pt; }
th, td { border: 1px solid #d0d7de; padding: 2px 4px; vertical-align: top; text-align: left; }
th { background: #f6f8fa; }
code { font-family: Consolas, monospace; font-size: 0.86em; background: #f6f8fa; padding: 0 2px; }
strong { font-weight: 600; }
"""

def main() -> None:
    body = markdown.markdown(
        (ROOT / "SOLUTION.md").read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )
    html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
    (OUT / "SOLUTION.html").write_text(html, encoding="utf-8")
    print(OUT / "SOLUTION.html")

if __name__ == "__main__":
    main()
