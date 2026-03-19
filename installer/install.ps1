#Requires -Version 5.1
<#
.SYNOPSIS
    pep# Beta Installer for Windows
.DESCRIPTION
    Installs the pep# CLI to the user PATH so you can run:
        pep run script.pep
        pep watch script.pep --pipeline name
        pep plan script.pep --mode cluster
        pep compile script.pep
        pep repl
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root     = Split-Path $PSScriptRoot -Parent
$VenvDir  = Join-Path $Root ".venv"
$BinDir   = Join-Path $env:USERPROFILE ".pep\bin"
$BatFile  = Join-Path $BinDir "pep.bat"
$PepVer   = "0.1.0-beta"

function Write-Banner {
    Write-Host ""
    Write-Host "  ██████╗ ███████╗██████╗ #" 
    Write-Host "  ██╔══██╗██╔════╝██╔══██╗" 
    Write-Host "  ██████╔╝█████╗  ██████╔╝" 
    Write-Host "  ██╔═══╝ ██╔══╝  ██╔═══╝ " 
    Write-Host "  ██║     ███████╗██║      " 
    Write-Host "  ╚═╝     ╚══════╝╚═╝     " 
    Write-Host ""
    Write-Host "  pep# Language Installer  v$PepVer" -ForegroundColor White
    Write-Host "  Pipeline-first. Parallel by default." -ForegroundColor DarkGray
    Write-Host ""
}

function Step($msg) {
    Write-Host "  >> $msg" -ForegroundColor DarkCyan
}

function Ok($msg) {
    Write-Host "  ok $msg" -ForegroundColor Green
}

function Fail($msg) {
    Write-Host "  !! $msg" -ForegroundColor Red
    exit 1
}

# ── Python check ──────────────────────────────────────────────────────────────
function Assert-Python {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        $py = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $py) {
        Fail "Python 3.10+ not found. Install from https://python.org"
    }
    $ver = & $py.Source --version 2>&1
    Ok "Python found: $ver"
    return $py.Source
}

# ── Virtual environment ───────────────────────────────────────────────────────
function Ensure-Venv ($python) {
    if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
        Step "Creating virtual environment in $VenvDir"
        & $python -m venv $VenvDir
    } else {
        Ok "Virtual environment already exists"
    }
}

# ── Install package ───────────────────────────────────────────────────────────
function Install-Package {
    $pip = Join-Path $VenvDir "Scripts\pip.exe"
    Step "Installing pep# package (editable mode)"
    & $pip install -e $Root --quiet
    Ok "Package installed"
}

# ── Create launcher BAT ───────────────────────────────────────────────────────
function Create-Launcher {
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    $python = Join-Path $VenvDir "Scripts\python.exe"
    $bat = "@echo off`r`n`"$python`" -m pep_lang.cli %*"
    Set-Content -Path $BatFile -Value $bat -Encoding ASCII
    Ok "Launcher created: $BatFile"
}

# ── PATH registration ─────────────────────────────────────────────────────────
function Register-Path {
    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -like "*$BinDir*") {
        Ok "PATH already contains $BinDir"
    } else {
        [Environment]::SetEnvironmentVariable("PATH", "$userPath;$BinDir", "User")
        Ok "Added $BinDir to user PATH"
    }
}

# ── Logo generation ───────────────────────────────────────────────────────────
function Generate-Logo {
    $script = Join-Path $Root "tools\generate_logo.py"
    $python  = Join-Path $VenvDir "Scripts\python.exe"
    if (Test-Path $script) {
        Step "Generating logo.png"
        & $python $script
    }
}

# ── Main ──────────────────────────────────────────────────────────────────────
Write-Banner

$python = Assert-Python
Ensure-Venv   $python
Install-Package
Create-Launcher
Register-Path
Generate-Logo

Write-Host ""
Write-Host "  pep# $PepVer installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "  Restart your terminal, then try:" -ForegroundColor White
Write-Host "    pep run examples/etl.pep" -ForegroundColor Yellow
Write-Host "    pep repl" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Install VS Code extension:" -ForegroundColor White
Write-Host "    .\installer\install-extension.ps1" -ForegroundColor Yellow
Write-Host ""
