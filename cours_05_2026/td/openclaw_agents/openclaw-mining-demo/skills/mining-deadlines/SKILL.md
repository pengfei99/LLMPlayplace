---
name: mining-deadlines
description: Extract investor deadlines from mining reports and generate CSV + ICS outputs.
---

# Mining Deadline Skill

Analyze documents in input_docs/.

Extract:
- permit renewals
- debt maturities
- feasibility study dates
- construction milestones
- production targets
- financing deadlines
- annual/quarterly reporting dates

Generate:

1. outputs/deadlines.csv
2. outputs/extraction_report.md
3. outputs/investor_calendar.ics

CSV columns:
- company
- project
- date
- title
- category
- importance
- source_document
- source_excerpt
- confidence
- notes

Rules:
- Use ISO date format YYYY-MM-DD
- Do not invent dates
- Approximate uncertain dates only when necessary
- High importance = financing / permits / production / material milestones
- Medium = reporting / updates
- Low = less critical dates

Use build_ics.py to generate the final calendar.