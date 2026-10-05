<#
.SYNOPSIS
  Veroeffentlicht eine neue Version (Windows): Version setzen, committen, Tag anlegen, optional hochladen.

.DESCRIPTION
  Ohne -Version wird die Version aus config.yaml verwendet (z. B. nach tools\sync_from_zip.ps1).
  -All     committet vorhandene Aenderungen vorher als "Update auf x.y.z"
  -Push    laedt Commit und Tag hoch
  Lokale Tests laufen hier nicht, GitHub fuehrt sie nach dem Hochladen aus (Reiter Actions).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\release.ps1 -All -Push
#>
param(
  [string]$Version = "",
  [switch]$All,
  [switch]$Push
)
$ErrorActionPreference = "Stop"
$utf8 = New-Object System.Text.UTF8Encoding($false)   # UTF-8 ohne BOM

function Fail([string]$msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

# Unerwartete Fehler verstaendlich melden statt mit einer PowerShell-Fehlerausgabe
trap { Write-Host ("Fehler: " + $_.Exception.Message) -ForegroundColor Red; exit 1 }

# git aufrufen und den Rueckgabewert pruefen (stderr von git ist kein PowerShell-Fehler)
function Invoke-Git {
  $old = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try { & git @args; $code = $LASTEXITCODE } finally { $ErrorActionPreference = $old }
  if ($code -ne 0) { throw ("git " + ($args -join " ") + " ist fehlgeschlagen (Code $code)") }
}
function Test-Git {   # true, wenn der Befehl erfolgreich ist; keine Ausgabe
  $old = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try { & git @args *> $null; return ($LASTEXITCODE -eq 0) } finally { $ErrorActionPreference = $old }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git ist nicht installiert (winget install --id Git.Git -e)." }
$Repo = Split-Path -Parent $PSScriptRoot
Set-Location $Repo
if (-not (Test-Git rev-parse --is-inside-work-tree)) {
  Fail ("Dieser Ordner ist kein Git-Repository (es fehlt das versteckte .git).`n" +
        "Hole dir eine Arbeitskopie:  gh repo clone DEIN-NAME/solasi `$HOME\solasi-git")
}

# Add-on-Ordner finden
$addon = $null
foreach ($d in @(Get-ChildItem $Repo -Directory)) {
  if ($d.Name -in @("tools", ".github")) { continue }
  if (Test-Path (Join-Path $d.FullName "config.yaml")) { $addon = $d.Name; break }
}
if (-not $addon) { Fail "Kein Add-on-Ordner mit config.yaml gefunden." }
$cfgPath = Join-Path (Join-Path $Repo $addon) "config.yaml"
$logPath = Join-Path (Join-Path $Repo $addon) "CHANGELOG.md"

if (-not $Version) {
  $Version = [regex]::Match([System.IO.File]::ReadAllText($cfgPath, $utf8), '(?m)^version:\s*"?([^"\r\n]*)"?').Groups[1].Value
  Write-Host "Verwende die Version aus config.yaml: $Version"
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') { Fail "Ungueltige Version: $Version (erwartet x.y.z)" }

# Uncommittete Aenderungen
$dirty = (& git status --porcelain) | Out-String
if ($dirty.Trim()) {
  if ($All) {
    Invoke-Git add -A
    Invoke-Git commit -q -m "Update auf $Version"
    Write-Host "Aenderungen als Update auf $Version committet."
  } else {
    Write-Host $dirty
    Fail "Es gibt uncommittete Aenderungen. Bitte erst committen oder -All verwenden."
  }
}

if (-not (Select-String -Path $logPath -Pattern ('^## ' + [regex]::Escape($Version) + '\s*$') -Quiet)) {
  Fail "In $addon\CHANGELOG.md fehlt der Abschnitt '## $Version'."
}
if (Test-Git rev-parse "v$Version") { Fail "Tag v$Version gibt es schon. Wurde diese Version schon veroeffentlicht?" }

Write-Host "Lokale Tests werden unter Windows uebersprungen. GitHub fuehrt sie nach dem Hochladen aus (Reiter Actions)."

# Version setzen, committen, taggen
$text = [System.IO.File]::ReadAllText($cfgPath, $utf8)
$text = [regex]::Replace($text, '(?m)^version:[^\r\n]*', "version: `"$Version`"")
[System.IO.File]::WriteAllText($cfgPath, $text, $utf8)
Invoke-Git add "$addon/config.yaml"
Invoke-Git commit -q -m "Release $Version" --allow-empty
Invoke-Git tag -a "v$Version" -m "SOLASI $Version"
Write-Host "Fertig: Version $Version committet und getaggt." -ForegroundColor Green

if ($Push) {
  try {
    Invoke-Git push
    Invoke-Git push origin "v$Version"
  } catch {
    Write-Host ""
    Write-Host ("Das Hochladen ist fehlgeschlagen: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host "Commit und Tag sind lokal angelegt. Pruefe die Anmeldung (gh auth status, bei Bedarf gh auth setup-git) und wiederhole nur:"
    Write-Host "  git push ; git push origin v$Version"
    exit 1
  }
  Write-Host "Hochgeladen. GitHub Actions legt das Release an."
} else {
  Write-Host "Zum Hochladen:  git push ; git push origin v$Version"
}
