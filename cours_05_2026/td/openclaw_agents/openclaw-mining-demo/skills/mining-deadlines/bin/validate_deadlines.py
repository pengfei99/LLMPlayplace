#!/usr/bin/env python3
import csv
import sys
from datetime import datetime
from pathlib import Path

REQUIRED_COLUMNS = [
    "company",
    "project",
    "date",
    "title",
    "category",
    "importance",
    "source_document",
    "source_excerpt",
    "confidence",
    "notes",
]

VALID_IMPORTANCE = {"High", "Medium", "Low"}


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_deadlines.py <deadlines.csv>")
        sys.exit(1)

    path = Path(sys.argv[1]).resolve()
    errors = []

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            errors.append(f"Missing columns: {missing}")

        rows = list(reader)
        if not rows:
            errors.append("CSV contains no rows.")

        for i, row in enumerate(rows, start=2):
            for col in REQUIRED_COLUMNS:
                if not row.get(col, "").strip():
                    errors.append(f"Line {i}: missing value for {col}")

            try:
                datetime.strptime(row.get("date", ""), "%Y-%m-%d")
            except Exception:
                errors.append(f"Line {i}: invalid date {row.get('date')}")

            if row.get("importance") not in VALID_IMPORTANCE:
                errors.append(f"Line {i}: invalid importance {row.get('importance')}")

            try:
                conf = float(row.get("confidence", ""))
                if conf < 0 or conf > 1:
                    errors.append(f"Line {i}: confidence outside [0,1]")
            except Exception:
                errors.append(f"Line {i}: invalid confidence")

    if errors:
        print("VALIDATION FAILED")
        for e in errors:
            print(f"- {e}")
        sys.exit(1)

    print("VALIDATION OK")


if __name__ == "__main__":
    main()
