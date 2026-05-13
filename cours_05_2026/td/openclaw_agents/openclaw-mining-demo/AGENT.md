# Workflow

## Required scripts to implement

The agent must create or complete the following scripts inside:

`skills/mining-deadlines/bin/`

-   `extract_text.py` --- Extract raw text from PDF files
-   `validate_deadlines.py` --- Validate deadlines CSV structure and
    required fields
-   `build_ics.py` --- Convert validated deadlines CSV into an investor
    calendar (.ics)

------------------------------------------------------------------------

## Execution pipeline

### 1. Extract PDF text

``` bash
python skills/mining-deadlines/bin/extract_text.py
```

### 2. Analyze extracted text files

Analyze files in:

`outputs/text/`

Process them one by one to avoid TPM/API token limits.

### 3. Extract investor-relevant deadlines

Identify all relevant filing dates, investor deadlines, and compliance
milestones.

### 4. Write CSV output

Generate:

`outputs/deadlines.csv`

### 5. Validate CSV

``` bash
python skills/mining-deadlines/bin/validate_deadlines.py outputs/deadlines.csv
```

### 6. Fix validation issues if needed

-   Correct malformed rows
-   Re-run validation until successful

### 7. Generate ICS calendar

``` bash
python skills/mining-deadlines/bin/build_ics.py outputs/deadlines.csv outputs/investor_calendar.ics
```

### 8. Write final extraction report

Generate:

`outputs/extraction_report.md`

------------------------------------------------------------------------

## Final deliverables

-   `outputs/deadlines.csv`
-   `outputs/investor_calendar.ics`
-   `outputs/extraction_report.md`

------------------------------------------------------------------------

## Important implementation note

Any script referenced in the workflow should be explicitly included as a
required deliverable; otherwise, the agent may incorrectly assume it
already exists.