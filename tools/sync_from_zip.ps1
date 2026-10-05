<#
.SYNOPSIS
  Spielt ein neues Paket (solasi_repo.zip oder ein entpackter Ordner) in die Git-Arbeitskopie ein (Windows).

.DESCRIPTION
  Ersetzt den Add-on-Ordner, .github, tools, README.md und DEVELOPMENT.md. Nicht angefasst werden repository.yaml und LICENSE.
  Die Projekt-URL in config.yaml bleibt erhalten.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\sync_from_zip.ps1 -Source "$HOME\Downloads\solasi_repo.zip" -Repo "$HOME\solasi-git"
#>
param(
  [Parameter(Mandatory = $true)][string]$Source,
  [string]$Repo = ""
)
$ErrorActionPreference = "Stop"
$utf8 = New-Object System.Text.UTF8Encoding($false)   # UTF-8 ohne BOM

function Fail([string]$msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

# Unerwartete Fehler verstaendlich melden statt mit einer PowerShell-Fehlerausgabe
trap { Write-Host ("Fehler: " + $_.Exception.Message) -ForegroundColor Red; exit 1 }

# --- Arbeitskopie bestimmen und pruefen ---
if (-not $Repo) { $Repo = Split-Path -Parent $PSScriptRoot }
if (-not (Test-Path $Repo)) { Fail "Der Ordner $Repo existiert nicht." }
$Repo = (Resolve-Path $Repo).Path
if (-not (Test-Path (Join-Path $Repo ".git"))) {
  Fail ("Dieser Ordner ist kein Git-Repository (es fehlt das versteckte .git): $Repo`n" +
        "Hole dir eine Arbeitskopie:  gh repo clone DEIN-NAME/solasi `$HOME\solasi-git   und gib sie mit -Repo an.")
}

# --- Paket entpacken (Zip) oder Ordner verwenden ---
$tmp = $null
if (-not (Test-Path $Source)) { Fail "Quelle nicht gefunden: $Source" }
$srcItem = Get-Item $Source
if ($srcItem.PSIsContainer) {
  $pkg = $srcItem.FullName
} else {
  $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("solasi-sync-" + [guid]::NewGuid().ToString("N"))
  Expand-Archive -Path $srcItem.FullName -DestinationPath $tmp -Force
  $pkg = $tmp
}

function Find-Addon([string]$dir) {
  foreach ($d in @(Get-ChildItem $dir -Directory -Force)) {
    if ($d.Name -in @("tools", ".github", ".git")) { continue }
    if (Test-Path (Join-Path $d.FullName "config.yaml")) { return $d.Name }
  }
  return $null
}

# Paketwurzel finden: direkt oder in einem Unterordner (z. B. solasi-repo)
$root = $null
$candidates = @($pkg) + @(Get-ChildItem $pkg -Directory -Force | ForEach-Object { $_.FullName })
foreach ($c in $candidates) { if (Find-Addon $c) { $root = $c; break } }
if (-not $root) { if ($tmp) { Remove-Item $tmp -Recurse -Force }; Fail "Das Paket enthaelt keinen Add-on-Ordner mit config.yaml." }
$addon = Find-Addon $root

# --- Projekt-URL aus der bisherigen config.yaml merken ---
$oldCfg = Join-Path (Join-Path $Repo $addon) "config.yaml"
$oldUrl = $null
if (Test-Path $oldCfg) {
  $m = [regex]::Match([System.IO.File]::ReadAllText($oldCfg, $utf8), '(?m)^url:[^\r\n]*')
  if ($m.Success) { $oldUrl = $m.Value }
}

# --- Ordner ersetzen ---
function Replace-Dir([string]$name) {
  $from = Join-Path $root $name
  if (-not (Test-Path $from)) { return }
  $to = Join-Path $Repo $name
  if (Test-Path $to) { Remove-Item $to -Recurse -Force }
  Copy-Item $from $to -Recurse -Force
  @(Get-ChildItem $to -Recurse -Force -Directory -ErrorAction SilentlyContinue) |
    Where-Object { $_.Name -in @("node_modules", "__pycache__", ".pytest_cache") } |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
}
Replace-Dir $addon
Replace-Dir ".github"
Replace-Dir "tools"

# --- Projekt-URL wiederherstellen ---
if ($oldUrl) {
  $newCfg = Join-Path (Join-Path $Repo $addon) "config.yaml"
  $text = [System.IO.File]::ReadAllText($newCfg, $utf8)
  $text = [regex]::Replace($text, '(?m)^url:[^\r\n]*', $oldUrl.Replace('$', '$$'))
  [System.IO.File]::WriteAllText($newCfg, $text, $utf8)
}

# --- fehlende Dateien auf oberster Ebene anlegen (vorhandene bleiben unveraendert) ---
foreach ($f in @("repository.yaml", "LICENSE", ".gitignore", ".gitattributes")) {
  $from = Join-Path $root $f
  $to = Join-Path $Repo $f
  if ((Test-Path $from) -and -not (Test-Path $to)) { Copy-Item $from $to; Write-Host "Neu angelegt: $f" }
}

# README.md und DEVELOPMENT.md gehoeren zum Paket und werden aktualisiert.
# Konto und Repository-Name kommen aus repository.yaml.
$owner = $null; $rname = $null
$repoYaml = Join-Path $Repo "repository.yaml"
if (Test-Path $repoYaml) {
  $mm = [regex]::Match([System.IO.File]::ReadAllText($repoYaml, $utf8), 'github\.com/([^/\s"]+)/([^/\s"]+)')
  if ($mm.Success) { $owner = $mm.Groups[1].Value; $rname = $mm.Groups[2].Value }
}
foreach ($f in @("README.md", "DEVELOPMENT.md")) {
  $from = Join-Path $root $f
  if (-not (Test-Path $from)) { continue }
  $text = [System.IO.File]::ReadAllText($from, $utf8)
  if ($owner) {
    $target = "github.com/$owner/$rname"
    $text = [regex]::Replace($text, 'github\.com/DEIN-NAME/[A-Za-z0-9._-]*', $target.Replace('$', '$$'))
    $text = [regex]::Replace($text, 'github\.com%2FDEIN-NAME%2F[A-Za-z0-9._-]*', ("github.com%2F" + $owner + "%2F" + $rname).Replace('$', '$$'))
    $text = $text.Replace("DEIN-NAME", $owner)
  }
  [System.IO.File]::WriteAllText((Join-Path $Repo $f), $text, $utf8)
}

if ($tmp) { Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue }

$ver = [regex]::Match([System.IO.File]::ReadAllText((Join-Path (Join-Path $Repo $addon) "config.yaml"), $utf8), '(?m)^version:\s*"?([^"\r\n]*)"?').Groups[1].Value
Write-Host ""
Write-Host "Eingespielt: $addon, Version $ver" -ForegroundColor Green
Write-Host "Aenderungen:"
& git -C $Repo status --short
Write-Host ""
Write-Host "Naechster Schritt (im Ordner $Repo):"
Write-Host "  powershell -ExecutionPolicy Bypass -File tools\release.ps1 -All -Push"
