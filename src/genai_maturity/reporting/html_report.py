from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


def render_html_report(
    template_path: Path,
    css_path: Path,
    output_path: Path,
    data: dict[str, Any],
) -> None:
    env = Environment(loader=FileSystemLoader(str(template_path.parent)))
    template = env.get_template(template_path.name)
    css_text = css_path.read_text(encoding="utf-8")
    rendered = template.render(css=css_text, data=data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
