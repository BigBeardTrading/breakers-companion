param(
  [string]$Path = "Version",
  [string]$Default = "2.0.24-test.1"
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $Path)) {
  Set-Content -LiteralPath $Path -Value $Default -Encoding ascii
  Write-Output $Default
  exit 0
}
$v = (Get-Content -LiteralPath $Path -Raw).Trim()
if ($v -match '^(\d+\.\d+\.\d+)-test\.(\d+)$') {
  $new = "$($Matches[1])-test.$([int]$Matches[2] + 1)"
} elseif ($v -match '^(\d+\.\d+\.\d+)$') {
  $new = "$($Matches[1])-test.1"
} else {
  $new = $Default
}
Set-Content -LiteralPath $Path -Value $new -Encoding ascii
Write-Output $new
