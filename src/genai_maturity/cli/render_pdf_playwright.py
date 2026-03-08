from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _render_with_python_playwright(input_html: Path, output_pdf: Path) -> None:
    from playwright.sync_api import sync_playwright  # type: ignore

    url = input_html.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.pdf(
            path=str(output_pdf),
            format="A4",
            print_background=True,
            margin={"top": "16mm", "right": "12mm", "bottom": "16mm", "left": "12mm"},
        )
        browser.close()


def _render_with_node_playwright(input_html: Path, output_pdf: Path) -> None:
    script = r"""
const { chromium } = require('playwright');
(async () => {
  const input = process.argv[1];
  const output = process.argv[2];
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const url = 'file://' + input;
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.pdf({
    path: output,
    format: 'A4',
    printBackground: true,
    margin: { top: '16mm', right: '12mm', bottom: '16mm', left: '12mm' }
  });
  await browser.close();
})();
"""
    subprocess.run(
        ["node", "-e", script, str(input_html.resolve()), str(output_pdf.resolve())],
        check=True,
        capture_output=True,
        text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render HTML report to PDF using Playwright Chromium.")
    parser.add_argument("--input-html", required=True)
    parser.add_argument("--output-pdf", required=True)
    args = parser.parse_args()

    input_html = Path(args.input_html)
    output_pdf = Path(args.output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    python_error: Exception | None = None
    try:
        _render_with_python_playwright(input_html, output_pdf)
        print(f"PDF generated: {output_pdf}")
        return 0
    except Exception as exc:  # noqa: BLE001
        python_error = exc

    try:
        _render_with_node_playwright(input_html, output_pdf)
        print(f"PDF generated: {output_pdf}")
        return 0
    except Exception as node_error:  # noqa: BLE001
        print(
            "Could not render PDF with Playwright. "
            "Install Playwright (Python or Node) and Chromium browser, then retry.",
            file=sys.stderr,
        )
        if python_error is not None:
            print(f"Python Playwright error: {python_error}", file=sys.stderr)
        print(f"Node Playwright error: {node_error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
