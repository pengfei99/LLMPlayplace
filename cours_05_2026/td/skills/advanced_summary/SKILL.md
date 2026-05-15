---
name: advanced_summary
description: Scan a directory and reply with a structured summary including a file tree, type breakdown, and README excerpt.
metadata: {"openclaw": {"emoji": "🔍", "requires": {"bins": ["python3"]}}}
---

# Advanced Summary

## Instructions

When this skill is invoked, the user must provide a directory path to scan. If they don't, ask for it.

Run:

```bash
output=$(python3 "$(dirname "$0")/summarize.py" <directory> 2>/dev/null)
```

Then reply with:

```
{$output}
```

After the script output, add a short **"Inferred purpose"** paragraph (2–4 sentences) based on the file previews — what the folder likely does, its main language/stack, and anything notable. Keep it concise.
