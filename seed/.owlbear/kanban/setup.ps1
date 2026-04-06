<#
.SYNOPSIS
  Download portable tools for the Graphicator project.
.DESCRIPTION
  Downloads kanban-md into the kanban/ directory.
  Run from any directory — the script resolves paths relative to itself.
#>
$ErrorActionPreference = 'Stop'
$kanbanDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# --- kanban-md ---
$kanbanVersion = '0.33.0'
$kanbanExe = Join-Path $kanbanDir 'kanban-md.exe'

if (Test-Path $kanbanExe) {
  $current = & $kanbanExe --version 2>&1 | Select-String -Pattern '[\d.]+' |
  ForEach-Object { $_.Matches[0].Value }
  if ($current -eq $kanbanVersion) {
    Write-Host "kanban-md $kanbanVersion already installed." -ForegroundColor Green
    return
  }
}

Write-Host "Downloading kanban-md $kanbanVersion ..." -ForegroundColor Cyan
$zipUrl = "https://github.com/antopolskiy/kanban-md/releases/download/v$kanbanVersion/kanban-md_${kanbanVersion}_windows_amd64.zip"
$zipPath = Join-Path $env:TEMP "kanban-md-$kanbanVersion.zip"
$extractDir = Join-Path $env:TEMP "kanban-md-$kanbanVersion"

$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing

if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
Copy-Item (Join-Path $extractDir 'kanban-md.exe') $kanbanExe -Force

# Cleanup
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "kanban-md $kanbanVersion installed to $kanbanExe" -ForegroundColor Green
