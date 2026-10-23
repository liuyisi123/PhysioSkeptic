"""Package selected tracked public source files, not the working directory."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOTS = {
    "src",
    "scripts",
    "tests",
    "prompts",
    "configs",
    "docs",
    "demo",
    "assets",
    "physioskeptic_ui",
    ".github",
}
PUBLIC_FILES = {
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "pyproject.toml",
    "requirements.txt",
    ".gitignore",
    "data/README.md",
    "data/patch_report.schema.json",
    "data/sample_patch_report.json",
}
PRIVATE_PARTS = {
    ".git",
    "__pycache__",
    ".venv",
    "outputs",
    "runs",
    "checkpoints",
    "weights",
    "logs",
    "build",
    "dist",
}
PRIVATE_SUFFIXES = {
    ".pyc",
    ".pt",
    ".pth",
    ".bin",
    ".ckpt",
    ".safetensors",
    ".gguf",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".jsonl",
    ".pem",
    ".key",
}


def public_path(name: str) -> bool:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return False
    if any(part in PRIVATE_PARTS for part in path.parts):
        return False
    if path.suffix.lower() in PRIVATE_SUFFIXES or path.name.startswith(".env"):
        return False
    return name in PUBLIC_FILES or (bool(path.parts) and path.parts[0] in PUBLIC_ROOTS)


def create_archive(output: Path, root: Path = ROOT) -> list[str]:
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode("utf-8").split("\0")
    selected = sorted(name for name in names if name and public_path(name))
    if not selected:
        raise RuntimeError("No tracked public source files found")
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Archive already exists: {output}")
    for name in selected:
        source = root / name
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Expected a regular tracked file: {name}")
        if not source.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Source is outside the repository: {name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
        for name in selected:
            archive.write(root / name, "PhysioSkeptic/" + name)
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/PhysioSkeptic-source.zip")
    args = parser.parse_args()
    names = create_archive(args.output)
    print(f"Packaged {len(names)} tracked public files: {args.output}")


if __name__ == "__main__":
    main()
