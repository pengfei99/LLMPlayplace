import ollama
import os
import re

MODEL = "gemma4"

SYSTEM_PROMPT = """
You are a senior web developer.

Generate a complete small website based on user requirements.

Return ONLY these sections:

=== index.html ===
<html code>

=== style.css ===
<css code>

=== script.js ===
<javascript code>

Do not explain anything.
"""

user_request = input("Describe the website you want:\n> ")

response = ollama.chat(
    model=MODEL,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_request},
    ]
)

content = response["message"]["content"]


def extract_section(name):
    pattern = rf"=== {name} ===\n(.*?)(?=\n===|\Z)"
    match = re.search(pattern, content, re.S)
    return match.group(1).strip() if match else ""


files = {
    "index.html": extract_section("index.html"),
    "style.css": extract_section("style.css"),
    "script.js": extract_section("script.js"),
}

os.makedirs("output", exist_ok=True)

for filename, code in files.items():
    with open(f"output/{filename}", "w") as f:
        f.write(code)

print("\nWebsite generated in ./output/")