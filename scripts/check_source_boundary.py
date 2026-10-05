"""Check release source boundaries; report filenames only, never matched secret values."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

paths = set(subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard", "-z"]).decode().split("\0"))
patterns = [
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"ghp_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{40,}",
    r"sk-[A-Za-z0-9]{32,}", r"AKIA[0-9A-Z]{16}",
]
flagged = []
for name in sorted(paths):
    if not name:
        continue
    path = Path(name)
    if not path.is_file():
        continue
    if path.name == ".env" or path.stat().st_size > 10*1024*1024:
        flagged.append(name); continue
    if path.suffix.lower() in {".png", ".jpg", ".ico", ".woff", ".ttf"}:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    if any(re.search(pattern, text) for pattern in patterns):
        flagged.append(name)
print({"candidate_files":len(paths)-1,"flagged_filenames":flagged})
if flagged:
    raise SystemExit(1)
