"""Check repository documentation links and GitHub-style section anchors.

Uses only the Python standard library and makes no network requests.
"""
from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if value and key in {"href", "src"}:
                self.targets.append(value)
            if value and key in {"id", "name"}:
                self.ids.add(value)


def visible(text: str) -> str:
    return re.sub(r"^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", "", text,
                  flags=re.M | re.S)


def anchors(path: Path) -> set[str]:
    text = visible(path.read_text(encoding="utf-8"))
    html = Links()
    html.feed(text)
    result = html.ids
    used: Counter[str] = Counter()
    for title in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", text, re.M):
        title = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", title)
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        n = used[slug]
        used[slug] += 1
        result.add(slug + (f"-{n}" if n else ""))
    return result


def check() -> list[str]:
    files = [ROOT / "README.md", ROOT / "CONTRIBUTING.md"]
    for directory in ["docs", "data", "demo", "experiments"]:
        files.extend(sorted((ROOT / directory).rglob("*.md")))
    errors: list[str] = []
    count = 0
    for file in files:
        text = visible(file.read_text(encoding="utf-8"))
        html = Links()
        html.feed(text)
        targets = html.targets + re.findall(r"!?\[[^]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", text)
        for target in targets:
            parsed = urlsplit(target.strip("<>"))
            if parsed.scheme or parsed.netloc:
                continue
            count += 1
            dest = (file.parent / unquote(parsed.path)).resolve() if parsed.path else file
            if not dest.is_relative_to(ROOT):
                errors.append(f"{file.relative_to(ROOT)}: link escapes checkout: {target}")
            elif not dest.exists():
                errors.append(f"{file.relative_to(ROOT)}: missing target: {target}")
            elif parsed.fragment and dest.suffix.lower() == ".md":
                if unquote(parsed.fragment) not in anchors(dest):
                    errors.append(f"{file.relative_to(ROOT)}: missing section: {target}")
    print(f"Checked {len(files)} documentation files and {count} local links.")
    return errors


if __name__ == "__main__":
    problems = check()
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        raise SystemExit(1)
    print("Documentation links and anchors are valid.")
