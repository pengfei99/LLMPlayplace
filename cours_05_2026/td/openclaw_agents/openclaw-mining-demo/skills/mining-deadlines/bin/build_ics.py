#!/usr/bin/env python3
import csv
import hashlib
import sys
from datetime import datetime, timedelta
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


def escape_ics(text: str) -> str:
    text = text or ""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def fold_ics_line(line: str) -> str:
    # RFC5545 recommends max 75 octets; this simple version is fine for demos.
    if len(line) <= 75:
        return line
    parts = [line[:75]]
    rest = line[75:]
    while rest:
        parts.append(" " + rest[:74])
        rest = rest[74:]
    return "\r\n".join(parts)


def parse_date(date_str: str):
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def make_uid(row: dict) -> str:
    raw = "|".join(
        [
            row.get("company", ""),
            row.get("project", ""),
            row.get("date", ""),
            row.get("title", ""),
            row.get("source_document", ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24] + "@mining-demo.local"


def reminder_days(importance: str):
    importance = (importance or "").strip().lower()
    if importance == "high":
        return 14
    if importance == "medium":
        return 7
    return None


def row_to_event(row: dict) -> list[str]:
    event_date = parse_date(row["date"])
    next_day = event_date + timedelta(days=1)

    summary = f"{row['company']} - {row['title']}"
    description = (
        f"Category: {row.get('category', '')}\n"
        f"Project: {row.get('project', '')}\n"
        f"Importance: {row.get('importance', '')}\n"
        f"Confidence: {row.get('confidence', '')}\n"
        f"Source: {row.get('source_document', '')}\n\n"
        f"Excerpt: {row.get('source_excerpt', '')}\n\n"
        f"Notes: {row.get('notes', '')}"
    )

    lines = [
        "BEGIN:VEVENT",
        f"UID:{make_uid(row)}",
        f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;VALUE=DATE:{event_date.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}",
        f"SUMMARY:{escape_ics(summary)}",
        f"DESCRIPTION:{escape_ics(description)}",
        f"CATEGORIES:{escape_ics(row.get('category', 'Mining Deadline'))}",
    ]

    days = reminder_days(row.get("importance", ""))
    if days:
        lines.extend(
            [
                "BEGIN:VALARM",
                f"TRIGGER:-P{days}D",
                "ACTION:DISPLAY",
                f"DESCRIPTION:Reminder - {escape_ics(summary)}",
                "END:VALARM",
            ]
        )

    lines.append("END:VEVENT")
    return lines


def main():
    if len(sys.argv) < 3:
        print("Usage: build_ics.py <deadlines.csv> <output.ics>")
        sys.exit(1)

    csv_path = Path(sys.argv[1]).resolve()
    ics_path = Path(sys.argv[2]).resolve()

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        events = []
        for row in reader:
            if not row.get("date"):
                continue
            try:
                events.extend(row_to_event(row))
            except Exception as e:
                print(f"Skipping invalid row: {row} | error={e}")

    calendar_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Mining Deadline Agent Demo//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Mining Investor Deadlines",
    ]

    calendar_lines.extend(events)
    calendar_lines.append("END:VCALENDAR")

    ics_content = "\r\n".join(fold_ics_line(line) for line in calendar_lines) + "\r\n"
    ics_path.write_text(ics_content, encoding="utf-8")
    print(f"Wrote {ics_path}")


if __name__ == "__main__":
    main()
