"""Export the EGX Radar Python source tree into a single standalone file."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = ROOT / "EGX_RADAR_FULL_SOURCE.py"
OUTPUT_MD_FILE = ROOT / "EGX_RADAR_FULL_SOURCE.md"

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    ".vscode",
}

EXCLUDED_SUFFIXES = {
    ".bak",
    ".tmp",
}

EXCLUDED_FILES = {
    OUTPUT_FILE.name,
    OUTPUT_MD_FILE.name,
}


def should_export(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDED_DIRS:
        return False
    if path.name in EXCLUDED_FILES:
        return False
    if path.name.startswith("."):
        return False
    if not path.is_file() or path.suffix != ".py":
        return False
    if any(path.name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES):
        return False
    if ".bak_" in path.name:
        return False
    return True


def iter_source_files() -> list[Path]:
    files = [path for path in ROOT.rglob("*.py") if should_export(path)]
    return sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())


def build_export() -> str:
    lines: list[str] = []
    lines.append('"""Standalone consolidated source export for EGX Radar.')
    lines.append("")
    lines.append("This file is auto-generated from the current project tree.")
    lines.append("Each section starts with the original relative path.")
    lines.append('"""')
    lines.append("")

    for source_file in iter_source_files():
        relative_path = source_file.relative_to(ROOT).as_posix()
        content = source_file.read_text(encoding="utf-8", errors="ignore").rstrip()

        lines.append("#" + "=" * 78)
        lines.append(f"# FILE: {relative_path}")
        lines.append("#" + "=" * 78)
        lines.append("")
        if content:
            lines.append(content)
            lines.append("")
        else:
            lines.append("# Empty file")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_markdown_export() -> str:
    lines: list[str] = []
    lines.append("# EGX Radar Full Source Export")
    lines.append("")
    lines.append("This file is auto-generated from the current project tree.")
    lines.append("Each section contains the original relative path followed by the file content.")
    lines.append("")

    for source_file in iter_source_files():
        relative_path = source_file.relative_to(ROOT).as_posix()
        content = source_file.read_text(encoding="utf-8", errors="ignore").rstrip()

        lines.append(f"## {relative_path}")
        lines.append("")
        lines.append("```python")
        if content:
            lines.append(content)
        lines.append("```")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    OUTPUT_FILE.write_text(build_export(), encoding="utf-8")
    OUTPUT_MD_FILE.write_text(build_markdown_export(), encoding="utf-8")
    print(f"Exported consolidated source to: {OUTPUT_FILE}")
    print(f"Exported Markdown source to: {OUTPUT_MD_FILE}")


if __name__ == "__main__":
    main()