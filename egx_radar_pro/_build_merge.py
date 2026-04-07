import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "merged_egx_radar_pro_single.py"

FILE_ORDER = [
    "config/__init__.py",
    "config/settings.py",
    "utils/__init__.py",
    "utils/helpers.py",
    "utils/logger.py",
    "data/__init__.py",
    "data/loader.py",
    "news/__init__.py",
    "news/nlp_arabic.py",
    "news/sentiment_engine.py",
    "news/news_fetcher.py",
    "news/news_intelligence.py",
    "alpha/__init__.py",
    "alpha/alpha_filter.py",
    "alpha/alpha_engine.py",
    "alpha/alpha_execution.py",
    "core/__init__.py",
    "core/indicators.py",
    "core/market_regime.py",
    "core/smart_rank.py",
    "core/signal_engine.py",
    "risk/__init__.py",
    "risk/position_sizing.py",
    "risk/portfolio.py",
    "backtest/__init__.py",
    "backtest/engine.py",
    "backtest/metrics.py",
    "backtest/optimizer.py",
    "backtest/validator.py",
    "ai/__init__.py",
    "ai/probability_engine.py",
    "ai/learning.py",
    "ai/advisor.py",
    "main.py",
]

INTERNAL_IMPORT = re.compile(
    r"^(from|import)\s+(config|core|data|risk|backtest|alpha|ai|news|utils)(\.|\s|$)|^from\s+\."
)
IMPORT_LINE = re.compile(r"^(from\s+\S+\s+import\s+.+|import\s+.+)$")


def is_internal_import(line: str) -> bool:
    stripped = line.strip()
    return bool(INTERNAL_IMPORT.match(stripped))


def is_external_import(line: str) -> bool:
    stripped = line.strip()
    if stripped == "from __future__ import annotations":
        return False
    if is_internal_import(stripped):
        return False
    return bool(IMPORT_LINE.match(stripped))


def main() -> None:
    seen_imports: set[str] = set()
    ordered_imports: list[str] = []
    rendered_files: list[str] = []

    for rel_path in FILE_ORDER:
        file_path = ROOT / rel_path
        source_lines = file_path.read_text(encoding="utf-8").splitlines()
        body_lines: list[str] = []

        for line in source_lines:
            stripped = line.strip()
            if stripped == "from __future__ import annotations":
                continue
            if is_external_import(line):
                if stripped not in seen_imports:
                    seen_imports.add(stripped)
                    ordered_imports.append(stripped)
                continue
            if is_internal_import(line):
                continue
            body_lines.append(line)

        rendered_files.extend([
            "# =========================",
            f"# FILE: {rel_path}",
            "# =========================",
            *body_lines,
            "",
        ])

    final_lines = ["from __future__ import annotations", ""]
    final_lines.extend(ordered_imports)
    final_lines.append("")
    final_lines.extend(rendered_files)
    OUTPUT.write_text("\n".join(final_lines) + "\n", encoding="utf-8")
    print(OUTPUT.name)
    print(sum(1 for _ in OUTPUT.open("r", encoding="utf-8")))


if __name__ == "__main__":
    main()
