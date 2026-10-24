from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "physioskeptic_github.zip"
# Archive committed files only. A working-directory archive could include Git
# metadata, local settings, credentials or generated data outside version control.
subprocess.run(
    ["git", "archive", "--format=zip", f"--output={OUT}", "HEAD"],
    cwd=ROOT,
    check=True,
)
print(OUT)
