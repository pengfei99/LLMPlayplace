#!/usr/bin/env python3
from pathlib import Path

from pypdf import PdfReader

input_dir = Path("input_docs")
output_dir = Path("outputs/text")
output_dir.mkdir(parents=True, exist_ok=True)

for pdf in input_dir.glob("*.pdf"):
    reader = PdfReader(str(pdf))
    text = []
    for i, page in enumerate(reader.pages, start=1):
        text.append(f"\n\n--- PAGE {i} ---\n")
        text.append(page.extract_text() or "")
    out = output_dir / f"{pdf.stem}.txt"
    out.write_text("".join(text), encoding="utf-8")
    print(f"Wrote {out}")
