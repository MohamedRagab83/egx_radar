"""Fix garbled Unicode characters in backtest/report.py."""
import pathlib

path = pathlib.Path(r'd:\egx radar seprated\egx_radar\backtest\report.py')
src = path.read_text(encoding='utf-8')

# Map each garbled sequence (UTF-8 bytes decoded as cp1252) to the correct Unicode char
fixes = {
    # emoji: 📊 (U+1F4CA) → ðŸ"Š
    '\u00f0\u009f\u0093\u008a': '\U0001f4ca',
    # emoji: 💾 (U+1F4BE) → ðŸ'¾
    '\u00f0\u009f\u0092\u00be': '\U0001f4be',
    # em-dash: — (U+2014) → â€"
    '\u00e2\u0080\u0094': '\u2014',
    # ellipsis: … (U+2026) → â€¦
    '\u00e2\u0080\u00a6': '\u2026',
    # ▶ (U+25B6) → â–¶
    '\u00e2\u0096\u00b6': '\u25b6',
    # ✅ (U+2705) → âœ…
    '\u00e2\u009c\u0085': '\u2705',
}

changed = 0
for bad, good in fixes.items():
    count = src.count(bad)
    if count:
        src = src.replace(bad, good)
        print(f'Fixed {count}x: {repr(bad)} -> {repr(good)}')
        changed += count

if changed:
    path.write_text(src, encoding='utf-8')
    print(f'Saved {path} with {changed} total replacements.')
else:
    print('Nothing to fix — checking what non-ASCII chars are present:')
    hi = set(c for c in src if ord(c) > 127)
    for c in sorted(hi, key=ord):
        print(f'  U+{ord(c):04X}  {repr(c)}')
