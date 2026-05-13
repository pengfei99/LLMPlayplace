#!/usr/bin/env python3
"""
Extract deadlines from Newmont Q1 2026 documents and create CSV for build_ics.py
"""
import csv
import re
from datetime import datetime
from pathlib import Path

# Define the source directory
source_dir = Path("/home/alexandre/Code/ENSAE/cours_agents_td/openclaw_agents/openclaw-mining-demo/outputs/text")

# Extract deadlines from the documents
deadlines = []

def parse_date(text):
    """Extract year, month, day from text and return datetime.date object"""
    patterns = [
        (r'(\d{1,2})\s*(?:th|nd|rd|st)?,?\s*(\d{4})', lambda m: datetime.strptime(f"{m.group(1)}/{m.group(2)}", "%m/%Y").date()),
        (r'(\d{4})/(\d{2})/(\d{2})', lambda m: datetime.strptime(m.group(0), "%Y/%m/%d").date()),
    ]
    for pattern, func in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return func(match)
            except:
                pass
    return None

# Process each text file
for text_file in source_dir.glob("*.txt"):
    print(f"Processing {text_file.name}...")
    content = text_file.read_text()
    
    # Extract dividend payments
    dividends = re.findall(r'(\d{1,2})/(\d{1,2})/(\d{4}).*?Dividend|dividend|\$0\.\d+', content, re.IGNORECASE)
    for dividend in dividends:
        try:
            date = datetime.strptime(f"{dividend[0]}/{dividend[1]}/{dividend[2]}", "%m/%d/%Y").date()
            deadlines.append({
                "company": "Newmont Corporation",
                "project": "Shareholder Dividend",
                "date": date.strftime("%Y-%m-%d"),
                "title": f"Quarterly Dividend Payment - ${dividend[3]} per share" if len(dividend) > 3 else "Quarterly Dividend Payment",
                "category": "Financial",
                "importance": "high",
                "source_document": text_file.stem,
                "source_excerpt": "Dividend payment to shareholders",
                "confidence": "high",
                "notes": f"Dividend payment per share: {dividend[3] if len(dividend) > 3 else 'TBD'}"
            })
        except:
            pass
    
    # Extract project completion dates
    project_dates = re.findall(r'(late|end|September|October|November|December)?\s*(\d{4}),?\s*(exp|on track)?\s*(to)?\s*(complete|finish)', content, re.IGNORECASE)
    for project_date in project_dates:
        try:
            date_str = f"{project_date[1]}"
            if project_date[0]:
                date_str = f"{project_date[0].strip().title()} {date_str}"
            date = parse_date(content)
            if date:
                deadlines.append({
                    "company": "Newmont Corporation",
                    "project": f"Project: {project_date[3].strip().title() if project_date[3] else 'Tanami Expansion 2'}",
                    "date": date.strftime("%Y-%m-%d"),
                    "title": f"Project Completion - {project_date[3].strip().title() if project_date[3] else 'Tanami Expansion 2'}",
                    "category": "Operations",
                    "importance": "medium",
                    "source_document": text_file.stem,
                    "source_excerpt": project_date[4].strip() if len(project_date) > 4 else "",
                    "confidence": "medium",
                    "notes": f"Expected completion date"
                })
        except:
            pass

# Filter for unique deadlines only
unique_deadlines = {}
for deadline in deadlines:
    key = (deadline["company"], deadline["project"], deadline["date"])
    if key not in unique_deadlines:
        unique_deadlines[key] = deadline

# Write to CSV
csv_path = Path(source_dir.parent / "mining-deadlines.csv")
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["company", "project", "date", "title", "category", "importance", "source_document", "source_excerpt", "confidence", "notes"])
    writer.writeheader()
    for deadline in unique_deadlines.values():
        writer.writerow(deadline)

print(f"\nWrote {len(unique_deadlines)} deadlines to {csv_path}")
print("\nDeadlines extracted:")
for deadline in sorted(unique_deadlines.values(), key=lambda x: x["date"]):
    print(f"  - {deadline['date']}: {deadline['title']} ({deadline['project']})")
