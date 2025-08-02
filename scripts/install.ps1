$ErrorActionPreference = 'Stop'

Write-Host "Welcome to the ValuaScript Installer for Windows!"

# --- Configuration ---
$Repo = "Alessio2704/monte-carlo-simulator"
$InstallDir = [System.Environment]::GetFolderPath('MyDocuments') + "\ValuaScript-Tools"
$TempDir = New-Item -ItemType Directory -Path (Join-Path $env:TEMP ([System.Guid]::NewGuid().ToString()))
$AssetSuffix = "windows-x64"

# --- Fetch Latest Release URL ---
Write-Host "Fetching latest release..."
$LatestReleaseApiUrl = "https://api.github.com/repos/$Repo/releases/latest"
$DownloadUrl = (Invoke-RestMethod -Uri $LatestReleaseApiUrl).assets | Where-Object { $_.name -like "*$AssetSuffix.zip" } | Select-Object -ExpandProperty browser_download_url
if (-not $DownloadUrl) { Write-Error "Error: Could not find release for your system ($AssetSuffix)."; exit 1 }

# --- Download and Install vse ---
Write-Host "Downloading ValuaScript engine from: $DownloadUrl"
Invoke-WebRequest -Uri $DownloadUrl -OutFile "$TempDir\valuascript.zip"

if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
New-Item -ItemType Directory -Path $InstallDir | Out-Null
Expand-Archive -Path "$TempDir\valuascript.zip" -DestinationPath $InstallDir

Write-Host "Unblocking downloaded files..."
Get-ChildItem -Path $InstallDir -Recurse | Unblock-File

# --- Add vse to PATH ---
Write-Host "Adding ValuaScript engine (vse) to your PATH..."
$CurrentUserPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
if (($CurrentUserPath -split ';') -notcontains $InstallDir) {
    $NewPath = $CurrentUserPath + ";$InstallDir"
    [System.Environment]::SetEnvironmentVariable('Path', $NewPath, 'User')
    Write-Host "✅ 'vse' has been added to your PATH."
}

# --- Install vsc from PyPI ---
Write-Host "Installing Python dependencies and vsc compiler..."
try {
    pip install pipx
    pipx ensurepath
    pipx install valuascript-compiler
} catch {
    Write-Error "Failed to install vsc. Please ensure Python and pip are installed and in your PATH."
}

# --- Cleanup ---
Remove-Item -Recurse -Force $TempDir

Write-Host ""
Write-Host "✅ Installation complete!"
Write-Host "IMPORTANT: You must open a new terminal for all changes to take effect."