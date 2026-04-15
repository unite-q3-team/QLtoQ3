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
$LogoPng = Join-Path $RepoRoot "qltoq3\bundled\logo.png"
$BuildIconPath = Join-Path $RepoRoot "build\windows\out\qltoq3.ico"
$WizardSmallImagePath = Join-Path $RepoRoot "build\windows\out\wizard-small.bmp"

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
    New-Item -ItemType Directory -Path (Split-Path -Parent $BuildIconPath) -Force | Out-Null

    Invoke-CheckedPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-CheckedPython -Arguments @("-m", "pip", "install", ".", "pyinstaller")

    if (-not (Test-Path $LogoPng)) {
        throw ("Logo file not found: {0}" -f $LogoPng)
    }
    $env:QLTOQ3_LOGO_PNG = $LogoPng
    $env:QLTOQ3_ICON_PATH = $BuildIconPath
    Invoke-CheckedPython -Arguments @(
        "-c",
        "import os; from PIL import Image; Image.open(os.environ['QLTOQ3_LOGO_PNG']).save(os.environ['QLTOQ3_ICON_PATH'], format='ICO', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])"
    )
    $env:QLTOQ3_WIZARD_SMALL_PATH = $WizardSmallImagePath
    Invoke-CheckedPython -Arguments @(
        "-c",
        "import os; from PIL import Image; src=Image.open(os.environ['QLTOQ3_LOGO_PNG']).convert('RGBA'); resampling=getattr(Image, 'Resampling', Image); src.thumbnail((55,55), resampling.LANCZOS); bg=Image.new('RGB',(55,55),(28,28,28)); bg.paste(src,((55-src.width)//2,(55-src.height)//2),src); bg.save(os.environ['QLTOQ3_WIZARD_SMALL_PATH'], format='BMP')"
    )

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

    $LocalesSrc = Join-Path $RepoRoot "locales"
    if (Test-Path $LocalesSrc) {
        Copy-Item $LocalesSrc (Join-Path $PortableRoot "locales") -Recurse -Force
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
            "/DInstallerIconFile=$BuildIconPath" `
            "/DWizardSmallImageFile=$WizardSmallImagePath" `
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
