# Build script for FusionMCPBridge Windows MSI installer
# Requires: WiX Toolset v3.x (candle.exe and light.exe in PATH)
#           or WiX Toolset v4.x (wix.exe in PATH)

param(
    [string]$Version = "0.1.0",
    [string]$OutputDir = ".\output"
)

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

Write-Host "Building FusionMCPBridge MSI installer v$Version" -ForegroundColor Cyan
Write-Host "Source: $PluginRoot" -ForegroundColor Gray

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

# Check for WiX toolset
$wixV4 = Get-Command "wix" -ErrorAction SilentlyContinue
$wixV3Candle = Get-Command "candle" -ErrorAction SilentlyContinue
$wixV3Light = Get-Command "light" -ErrorAction SilentlyContinue

if ($wixV4) {
    Write-Host "Using WiX v4" -ForegroundColor Green

    # WiX v4 build command
    & wix build `
        -d "SourceDir=$PluginRoot" `
        -d "Version=$Version" `
        -o "$OutputDir\FusionMCPBridge-$Version-win64.msi" `
        "$ScriptDir\FusionMCPBridge.wxs"

    if ($LASTEXITCODE -ne 0) {
        throw "WiX build failed with exit code $LASTEXITCODE"
    }
}
elseif ($wixV3Candle -and $wixV3Light) {
    Write-Host "Using WiX v3" -ForegroundColor Green

    $objDir = "$OutputDir\obj"
    if (-not (Test-Path $objDir)) {
        New-Item -ItemType Directory -Path $objDir | Out-Null
    }

    # Compile .wxs to .wixobj
    & candle.exe `
        -dSourceDir="$PluginRoot" `
        -dVersion="$Version" `
        -o "$objDir\FusionMCPBridge.wixobj" `
        "$ScriptDir\FusionMCPBridge.wxs"

    if ($LASTEXITCODE -ne 0) {
        throw "Candle (WiX compiler) failed with exit code $LASTEXITCODE"
    }

    # Link .wixobj to .msi
    & light.exe `
        -o "$OutputDir\FusionMCPBridge-$Version-win64.msi" `
        "$objDir\FusionMCPBridge.wixobj"

    if ($LASTEXITCODE -ne 0) {
        throw "Light (WiX linker) failed with exit code $LASTEXITCODE"
    }

    # Cleanup obj directory
    Remove-Item -Recurse -Force $objDir
}
else {
    Write-Host "ERROR: WiX Toolset not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install WiX Toolset:" -ForegroundColor Yellow
    Write-Host "  Option 1 (WiX v4): dotnet tool install --global wix" -ForegroundColor Gray
    Write-Host "  Option 2 (WiX v3): https://wixtoolset.org/docs/wix3/" -ForegroundColor Gray
    exit 1
}

$msiPath = "$OutputDir\FusionMCPBridge-$Version-win64.msi"
if (Test-Path $msiPath) {
    $size = (Get-Item $msiPath).Length / 1KB
    Write-Host ""
    Write-Host "SUCCESS: Built $msiPath ($([math]::Round($size, 1)) KB)" -ForegroundColor Green
}
else {
    throw "MSI file was not created"
}
