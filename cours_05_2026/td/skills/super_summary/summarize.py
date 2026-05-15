#!/usr/bin/env python3
"""
Scan a directory and print a structured summary to stdout.
Usage: python3 summarize.py <directory>
"""

import os
import sys
from collections import Counter
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
MAX_README_LINES = 10
FILE_HEAD_LINES = 8
# Binary-ish extensions to skip when collecting file heads
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".exe", ".bin", ".wasm",
    ".mp3", ".mp4", ".wav", ".mov", ".ttf", ".woff", ".woff2",
}


def collect_files(root_dir):
    results = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            results.append(Path(root) / name)
    return results


def build_tree(root_dir, max_depth=2):
    lines = []
    root = Path(root_dir)

    def _walk(path, prefix, depth):
        if depth > max_depth:
            return
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
        for i, entry in enumerate(entries):
            if entry.name in SKIP_DIRS:
                continue
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                extension = "    " if i == len(entries) - 1 else "│   "
                _walk(entry, prefix + extension, depth + 1)

    lines.append(f"{root.name}/")
    _walk(root, "", 1)
    return "\n".join(lines)


def build_type_breakdown(files):
    counts = Counter(
        (path.suffix.lower() if path.suffix else "(no ext)")
        for path in files
    )
    lines = []
    for ext, count in sorted(counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {count:>4}  {ext}")
    return "\n".join(lines)


def collect_file_heads(root_dir, files):
    root = Path(root_dir)
    entries = []
    for path in files:
        if path.suffix.lower() in SKIP_EXTENSIONS:
            continue
        try:
            with open(path, errors="replace") as f:
                lines = []
                for _ in range(FILE_HEAD_LINES):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line.rstrip())
            if lines:
                rel = path.relative_to(root)
                entries.append((str(rel), "\n".join(lines)))
        except Exception:
            pass
    return entries


def read_readme(root_dir):
    for name in ("README.md", "README.txt", "README", "readme.md"):
        path = Path(root_dir) / name
        if path.exists():
            try:
                with open(path) as f:
                    lines = [l.rstrip() for l in f.readlines()[:MAX_README_LINES]]
                return "\n".join(lines)
            except Exception:
                pass
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: summarize.py <directory>", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    if not os.path.isdir(target):
        print(f"Error: '{target}' is not a valid directory", file=sys.stderr)
        sys.exit(1)

    files = collect_files(target)

    sections = []

    sections.append(f"## 📂 {Path(target).resolve()} — {len(files)} file(s)\n")

    sections.append("### Structure\n```\n" + build_tree(target) + "\n```")

    sections.append("### File types\n" + build_type_breakdown(files))

    readme = read_readme(target)
    if readme:
        sections.append("### README (first 10 lines)\n```\n" + readme + "\n```")

    heads = collect_file_heads(target, files)
    if heads:
        parts = []
        for rel, content in heads:
            parts.append(f"#### {rel}\n```\n{content}\n```")
        sections.append("### File previews (first 8 lines each)\n\n" + "\n\n".join(parts))

    print("\n\n".join(sections))
