param(
    [string]$Version = "",
    [switch]$BuildInstaller
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptRoot "..\..\"))
$DistRoot = Join-Path $RepoRoot "dist\windows"
$PyInstallerDist = Join-Path $DistRoot "pyinstaller"
$PyInstallerWork = Join-Path $RepoRoot "build\windows\out\pyinstaller-work"
$PortableRoot = Join-Path $DistRoot "portable\QLtoQ3"
$PortableZipDir = Join-Path $DistRoot "portable"
$InstallerOut = Join-Path $DistRoot "installer"
$CliSpec = Join-Path $RepoRoot "build\windows\pyinstaller\cli.spec"
$GuiSpec = Join-Path $RepoRoot "build\windows\pyinstaller\gui.spec"
$InstallerScript = Join-Path $RepoRoot "build\windows\installer\qltoq3.iss"

function Invoke-CheckedPython {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )
    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ("Python command failed with exit code {0}: python {1}" -f $LASTEXITCODE, ($Arguments -join " "))
    }
}

Push-Location $RepoRoot
try {
    if ([string]::IsNullOrWhiteSpace($Version)) {
        $Version = (python -c "import qltoq3; print(qltoq3.__version__)").Trim()
    }
    if ([string]::IsNullOrWhiteSpace($Version)) {
        throw "Unable to determine application version."
    }

    foreach ($dir in @($PyInstallerDist, $PyInstallerWork, $PortableRoot, $InstallerOut)) {
        if (Test-Path $dir) {
            Remove-Item $dir -Recurse -Force
        }
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    Invoke-CheckedPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-CheckedPython -Arguments @("-m", "pip", "install", ".", "pyinstaller")

    Invoke-CheckedPython -Arguments @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath", "$PyInstallerDist",
        "--workpath", "$PyInstallerWork",
        "$CliSpec"
    )

    Invoke-CheckedPython -Arguments @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath", "$PyInstallerDist",
        "--workpath", "$PyInstallerWork",
        "$GuiSpec"
    )

    Copy-Item (Join-Path $PyInstallerDist "qltoq3-cli.exe") $PortableRoot -Force
    Copy-Item (Join-Path $PyInstallerDist "qltoq3-gui.exe") $PortableRoot -Force

    $BundledSrc = Join-Path $RepoRoot "qltoq3\bundled"
    if (Test-Path $BundledSrc) {
        Copy-Item $BundledSrc (Join-Path $PortableRoot "bundled") -Recurse -Force
    }

    $ReadmePath = Join-Path $RepoRoot "README.md"
    if (Test-Path $ReadmePath) {
        Copy-Item $ReadmePath (Join-Path $PortableRoot "README.md") -Force
    }

    $PortableZip = Join-Path $PortableZipDir ("QLtoQ3-portable-{0}-win64.zip" -f $Version)
    if (Test-Path $PortableZip) {
        Remove-Item $PortableZip -Force
    }
    Compress-Archive -Path (Join-Path $PortableRoot "*") -DestinationPath $PortableZip

    if ($BuildInstaller) {
        $iscc = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
        if (-not $iscc) {
            throw "no inno setup compiler (iscc.exe) in PATH."
        }
        & $iscc.Source `
            "/DAppVersion=$Version" `
            "/DSourceDir=$PortableRoot" `
            "/DOutputDir=$InstallerOut" `
            "$InstallerScript"
        if ($LASTEXITCODE -ne 0) {
            throw ("inno setup compiler failed, code: {0}." -f $LASTEXITCODE)
        }
    }

    Write-Host "build done"
    Write-Host "portable zip: $PortableZip"
    if ($BuildInstaller) {
        Write-Host "installer dir: $InstallerOut"
    }
}
finally {
    Pop-Location
}
