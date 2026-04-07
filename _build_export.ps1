Set-Location "d:\egx radar seprated"
$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path

$allPy = Get-ChildItem -Path "egx_radar" -Recurse -File -Filter *.py | Where-Object {
  $_.FullName -notmatch '\\.venv\\|\\__pycache__\\|\\archive\\|\\experimental\\|\\tests\\|\\logs\\' -and
  $_.Name -notmatch '\.bak' -and
  $_.Name -notmatch '^test_'
} | ForEach-Object {
  $_.FullName.Substring($root.Length + 1).Replace('\','/')
}

$jsonCandidates = @(
  'source_settings.json',
  'brain_state.json',
  'scan_snapshot.json',
  'egx_radar/source_settings.json',
  'egx_radar/brain_state.json'
) | Where-Object { Test-Path $_ }

$entries = @(
  'egx_radar/main.py',
  'egx_radar/__main__.py',
  'egx_radar/dashboard/run.py'
) | Where-Object { Test-Path $_ }

function Rank-File([string]$p) {
  if ($p -like 'egx_radar/config/*') { return 10 }
  if ($p -like '*.json') { return 15 }
  if ($p -like 'egx_radar/core/*' -and $p -notlike '*/signals.py' -and $p -notlike '*/signal_engine.py' -and $p -notlike '*/risk.py' -and $p -notlike '*/portfolio.py') { return 20 }
  if ($p -like 'egx_radar/market_data/*' -or $p -like 'egx_radar/core/signals.py' -or $p -like 'egx_radar/core/signal_engine.py') { return 30 }
  if ($p -like 'egx_radar/core/risk.py' -or $p -like 'egx_radar/core/portfolio.py' -or $p -like 'egx_radar/core/*guard.py' -or $p -like 'egx_radar/core/alpha_monitor.py' -or $p -like 'egx_radar/core/position_manager.py' -or $p -like 'egx_radar/advanced/risk_management.py') { return 40 }
  if ($p -like 'egx_radar/backtest/*') { return 50 }
  if ($p -like 'egx_radar/scan/*' -or $p -like 'egx_radar/outcomes/*' -or $p -like 'egx_radar/data/*' -or $p -like 'egx_radar/database/*' -or $p -like 'egx_radar/state/*' -or $p -like 'egx_radar/tools/*') { return 60 }
  if ($p -like 'egx_radar/dashboard/*' -or $p -like 'egx_radar/ui/*') { return 70 }
  if ($p -in @('egx_radar/main.py','egx_radar/__main__.py','egx_radar/__init__.py')) { return 80 }
  return 75
}

$orderedPy = $allPy | Sort-Object @{Expression={Rank-File $_}}, @{Expression={$_}}
$missing = Compare-Object -ReferenceObject ($allPy | Sort-Object) -DifferenceObject ($orderedPy | Sort-Object) | Where-Object { $_.SideIndicator -eq '<=' }
if ($missing) { throw "Missing Python files in ordered set." }
$dupPy = $orderedPy | Group-Object | Where-Object { $_.Count -gt 1 }
if ($dupPy) { throw "Duplicate Python files in ordered set." }

$allIncluded = @($orderedPy + $jsonCandidates)
$outFile = 'EGX_RADAR_FULL_CODE_EXPORT.md'
$sb = New-Object System.Text.StringBuilder

$null = $sb.AppendLine('EGX RADAR CODEBASE EXPORT')
$null = $sb.AppendLine('')
$null = $sb.AppendLine("TOTAL FILES: $($allIncluded.Count)")
$null = $sb.AppendLine('INCLUDED MODULES:')
foreach ($f in $allIncluded) { $null = $sb.AppendLine("- $f") }
$null = $sb.AppendLine('DETECTED ENTRY POINTS:')
foreach ($e in $entries) { $null = $sb.AppendLine("- $e") }
$null = $sb.AppendLine('')

foreach ($f in $allIncluded) {
  $title = "FILE: $f"
  $null = $sb.AppendLine('==================================================')
  $null = $sb.AppendLine($title)
  $null = $sb.AppendLine(('=' * $title.Length))
  $null = $sb.AppendLine('')
  if ($f -like '*.json') { $null = $sb.AppendLine('```json') } else { $null = $sb.AppendLine('```python') }
  $content = Get-Content -Raw -LiteralPath $f
  $null = $sb.AppendLine($content.TrimEnd("`r", "`n"))
  $null = $sb.AppendLine('```')
  $null = $sb.AppendLine('')
}

[System.IO.File]::WriteAllText((Join-Path $root $outFile), $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))
Write-Output "WROTE:$outFile"
Write-Output "TOTAL:$($allIncluded.Count)"
