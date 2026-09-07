#!/usr/bin/env python3
"""Verify that file paths mentioned in the skill's own docs actually exist.

Scans skills/korean-plain-writer/{SKILL.md,references/*.md,examples/**/*.md}
(everything except the vendored vendor/humanizer/ tree, whose paths are
relative to its own upstream root, not ours) for backtick-quoted paths that
look like references to files inside the skill, and checks each one exists
relative to skills/korean-plain-writer/.

Usage:
    python scripts/check_references.py
"""

from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO_ROOT / "skills" / "korean-plain-writer"

# Require at least one "/": bare filenames ("genre-rules.md" named in prose,
# or a sibling file cited from within its own directory) are too ambiguous to
# resolve from a single root, so this only checks multi-segment paths.
PATH_RE = re.compile(r"`([A-Za-z0-9_\-]+(?:/[A-Za-z0-9_.\-*]*)+)`")

SKIP_PREFIXES = ("http://", "https://")
# Paths inside the vendored tree resolve against its own upstream root, not
# ours; "skills/humanizer/" is DaleSeo/korean-skills' own internal path,
# mentioned in prose for provenance, not a path in this repo.
SKIP_PATH_PREFIXES = ("vendor/", "skills/humanizer/")


def candidate_paths(text: str) -> set[str]:
    found = set()
    for match in PATH_RE.finditer(text):
        path = match.group(1)
        if path.startswith(SKIP_PREFIXES):
            continue
        if path.startswith(SKIP_PATH_PREFIXES) or "/vendor/" in path:
            continue
        found.add(path)
    return found


def exists_relative_to_skill_root(path: str) -> bool:
    if "*" in path:
        return len(glob.glob(str(SKILL_ROOT / path))) > 0
    full = SKILL_ROOT / path
    return full.exists()


def main() -> int:
    md_files = [SKILL_ROOT / "SKILL.md"]
    md_files += sorted((SKILL_ROOT / "references").glob("*.md"))
    md_files += sorted((SKILL_ROOT / "examples").rglob("*.md"))

    missing: list[tuple[str, str]] = []
    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        for path in sorted(candidate_paths(text)):
            if not exists_relative_to_skill_root(path):
                missing.append((str(md_file.relative_to(REPO_ROOT)), path))

    if missing:
        print("Broken references found:")
        for source, path in missing:
            print(f"  {source} -> {path}")
        return 1

    print(f"OK: checked {len(md_files)} files, all referenced paths exist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
