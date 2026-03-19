#Requires -Version 5.1
<#
.SYNOPSIS
    Installs the pep# VS Code extension to the local extensions folder.
    No vsce or npm required — files are copied directly.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root      = Split-Path $PSScriptRoot -Parent
$ExtSrc    = Join-Path $Root "vscode-pep-sharp"
$ExtDest   = Join-Path $env:USERPROFILE ".vscode\extensions\pep-sharp.vscode-pep-sharp-0.1.0-beta"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$LogoScript = Join-Path $Root "tools\generate_logo.py"

function Step($msg) { Write-Host "  >> $msg" -ForegroundColor DarkCyan }
function Ok($msg)   { Write-Host "  ok $msg" -ForegroundColor Green }


Write-Host ""
Write-Host "  pep# VS Code Extension Installer" -ForegroundColor Cyan
Write-Host ""

# ── Generate logo ─────────────────────────────────────────────────────────────
if (Test-Path $LogoScript) {
    $py = if (Test-Path $VenvPython) { $VenvPython } else { (Get-Command python).Source }
    Step "Generating logo.png"
    & $py $LogoScript
}

# ── Copy extension ────────────────────────────────────────────────────────────
Step "Installing extension to $ExtDest"

if (Test-Path $ExtDest) {
    Remove-Item -Recurse -Force $ExtDest
}

Copy-Item -Recurse $ExtSrc $ExtDest

Ok "Extension installed"

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  Extension installed!" -ForegroundColor Green
Write-Host ""
Write-Host "  Reload VS Code (Ctrl+Shift+P > Developer: Reload Window)." -ForegroundColor White
Write-Host "  .pep files will now have syntax highlighting and autocomplete." -ForegroundColor White
Write-Host ""
