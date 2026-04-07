"""Fix garbled Unicode in backtest/report.py.
These chars were corrupted when the file was read as cp1252 instead of UTF-8.
The file currently stores them as cp1252-decoded Unicode code points.
"""
import pathlib

path = pathlib.Path(r'd:\egx radar seprated\egx_radar\backtest\report.py')
src = path.read_text(encoding='utf-8')

# Print what non-ASCII chars are actually present
hi = {}
for c in src:
    if ord(c) > 127:
        hi[c] = hi.get(c, 0) + 1

print("Non-ASCII characters in file:")
for c, n in sorted(hi.items(), key=lambda x: ord(x[0])):
    print(f"  U+{ord(c):04X}  {repr(c)}  count={n}")

# Map: garbled multi-char sequence -> correct Unicode char
# --- Em-dash U+2014 (UTF-8: E2 80 94) decoded as cp1252: â(E2) + euro(80) + right-dquote(94)
em_dash_bad  = '\u00e2\u20ac\u201d'   # â + € + "
em_dash_good = '\u2014'               # —

# --- Ellipsis U+2026 (UTF-8: E2 80 A6) decoded as cp1252: â(E2) + euro(80) + broken-bar(A6)
ellipsis_bad  = '\u00e2\u20ac\u00a6'  # â + € + ¦
ellipsis_good = '\u2026'              # …

# --- 📊 U+1F4CA (UTF-8: F0 9F 93 8A) decoded as cp1252: ð(F0) + Ÿ(9F) + ldquote(93) + Š(8A)
chart_bad  = '\u00f0\u0178\u201c\u0160'  # ðŸ"Š
chart_good = '\U0001f4ca'                # 📊

# --- 💾 U+1F4BE (UTF-8: F0 9F 92 BE) decoded as cp1252: ð(F0) + Ÿ(9F) + lsquote(92) + ¾(BE)
floppy_bad  = '\u00f0\u0178\u2018\u00be'  # ðŸ'¾
floppy_good = '\U0001f4be'                # 💾

# --- ▶ U+25B6 (UTF-8: E2 96 B6) decoded as cp1252: â(E2) + en-dash(96) + pilcrow(B6)
triangle_bad  = '\u00e2\u2013\u00b6'   # â–¶
triangle_good = '\u25b6'               # ▶

# --- ✅ U+2705 (UTF-8: E2 9C 85) decoded as cp1252: â(E2) + oe(9C) + ellipsis(85)
check_bad  = '\u00e2\u0153\u2026'     # âœ…  (note: 0x85 in cp1252 = U+2026 ellipsis)
check_good = '\u2705'                 # ✅

replacements = [
    (em_dash_bad,  em_dash_good),
    (ellipsis_bad, ellipsis_good),
    (chart_bad,    chart_good),
    (floppy_bad,   floppy_good),
    (triangle_bad, triangle_good),
    (check_bad,    check_good),
]

changed = 0
for bad, good in replacements:
    count = src.count(bad)
    if count:
        src = src.replace(bad, good)
        print(f"Fixed {count}x: {repr(bad)} -> {repr(good)}")
        changed += count
    else:
        print(f"Not found: {repr(bad)}")

if changed:
    path.write_text(src, encoding='utf-8')
    print(f"\nSaved with {changed} total replacements.")
else:
    print("\nNo replacements made. Check the mappings above against actual chars.")
