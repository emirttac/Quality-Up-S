# Quality Up'S — Windows release build (PyInstaller + Inno Setup)
# Run from anywhere:  powershell -ExecutionPolicy Bypass -File packaging/windows/build.ps1

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

Write-Host "=== Quality Up'S Windows build ===" -ForegroundColor Cyan

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    throw "Missing .venv. Run run.bat once to create the environment."
}

Write-Host "[1/3] Installing build dependencies..."
& $Py -m pip install -r (Join-Path $Root "requirements-build.txt")

Write-Host "[2/3] PyInstaller onedir bundle..."
& $Py -m PyInstaller `
    (Join-Path $Root "packaging\quality_ups.spec") `
    --noconfirm --clean `
    --distpath (Join-Path $Root "dist") `
    --workpath (Join-Path $Root "build\pyinstaller")

$Exe = Join-Path $Root "dist\QualityUps\QualityUps.exe"
if (-not (Test-Path $Exe)) {
    throw "PyInstaller output missing: $Exe"
}

Write-Host "[3/3] Inno Setup installer..."
$IsccCandidates = @(
    "$env:LocalAppData\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $Iscc) {
    Write-Warning "Inno Setup 6 not found (https://jrsoftware.org/isinfo.php)."
    Write-Host "PyInstaller bundle ready at dist\QualityUps\"
    exit 0
}

# Pass the 8.3 short path so the apostrophe in "Quality Up'S" cannot
# split Inno Setup's Pascal-quoted Source (unknown identifier "dist").
$Iss = Join-Path $Root "packaging\windows\QualityUps.iss"
$fso = New-Object -ComObject Scripting.FileSystemObject
$IssShort = $fso.GetFile($Iss).ShortPath
& $Iscc $IssShort
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "  App:       dist\QualityUps\QualityUps.exe"
Write-Host "  Installer: dist\installer\QualityUps-Setup-1.0.exe"
