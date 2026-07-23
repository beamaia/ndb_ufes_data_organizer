#!/usr/bin/env python3
"""Validate internal links, assets, anchors, search, and release downloads."""

from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


SITE_PREFIX = "/ndb_ufes_data_organizer/"
REQUIRED_SEARCH_TITLES = {
    "Thesis Experiment Design",
    "Canonical Experiment Results",
}
REQUIRED_DOWNLOADS = {
    "assets/experiments/canonical_run_manifest.json",
    "assets/experiments/fold_test_metrics.csv",
    "assets/experiments/results_summary.csv",
    "assets/experiments/execution_times.csv",
    "assets/experiments/statistics_within_experiment.csv",
    "assets/experiments/statistics_between_experiments.csv",
}


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[tuple[str, str]] = []
        self.anchors: set[str] = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ("id", "name"):
            if values.get(key):
                self.anchors.add(values[key])
        for key in ("href", "src"):
            if values.get(key):
                self.references.append((key, values[key]))


def target_for(site: Path, source: Path, url_path: str) -> Path:
    path = unquote(url_path)
    if path.startswith(SITE_PREFIX):
        path = path[len(SITE_PREFIX) :]
        target = site / path
    elif path.startswith("/"):
        target = site / path.lstrip("/")
    else:
        target = source.parent / path
    if path.endswith("/") or (not target.suffix and not target.is_file()):
        target = target / "index.html"
    return target.resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    html_files = sorted(site.rglob("*.html"))
    parsed: dict[Path, ReferenceParser] = {}
    for path in html_files:
        page = ReferenceParser()
        page.feed(path.read_text(encoding="utf-8"))
        parsed[path.resolve()] = page

    failures = []
    checked = 0
    for source, page in parsed.items():
        for _, reference in page.references:
            parts = urlsplit(reference)
            if parts.scheme or parts.netloc or reference.startswith(("#", "data:")):
                if reference.startswith("#") and reference[1:] not in page.anchors:
                    failures.append(f"{source}: missing local anchor {reference}")
                continue
            target = target_for(site, source, parts.path)
            checked += 1
            if not target.exists():
                failures.append(f"{source}: missing target {reference}")
                continue
            if parts.fragment and target.suffix == ".html":
                target_page = parsed.get(target)
                if target_page is None or parts.fragment not in target_page.anchors:
                    failures.append(
                        f"{source}: missing target anchor {reference}"
                    )

    search = json.loads(
        (site / "search/search_index.json").read_text(encoding="utf-8")
    )
    search_titles = {entry["title"] for entry in search["docs"]}
    missing_titles = REQUIRED_SEARCH_TITLES - search_titles
    if missing_titles:
        failures.append(f"search index missing titles: {sorted(missing_titles)}")

    for relative in REQUIRED_DOWNLOADS:
        if not (site / relative).is_file():
            failures.append(f"missing release download: {relative}")

    if failures:
        raise SystemExit("\n".join(failures))
    print(
        f"validated static site: {len(html_files)} HTML pages, "
        f"{checked} local references, search and downloads present"
    )


if __name__ == "__main__":
    main()
