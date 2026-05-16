from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "physioskeptic_github.zip"
if OUT.exists():
    OUT.unlink()
shutil.make_archive(str(OUT.with_suffix("")), "zip", ROOT)
print(OUT)
