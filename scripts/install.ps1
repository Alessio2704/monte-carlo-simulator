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
Write-Host "Installing the vsc compiler from PyPI..."
try {
    # Ensure Python is available
    Get-Command python | Out-Null
    
    Write-Host "Installing/upgrading pipx..."
    # Use 'python -m pip' for robustness and '--user' to avoid permission issues
    python -m pip install --user -q --upgrade pipx
    
    Write-Host "Ensuring pipx is in the PATH..."
    python -m pipx ensurepath
    
    Write-Host "Installing valuascript-compiler with pipx..."
    # The 'pipx' command should now be available
    pipx install valuascript-compiler

} catch {
    Write-Host ""
    Write-Host "❌ Error: Failed to install the 'vsc' compiler."
    Write-Host "Please ensure Python 3 is installed and that its 'Scripts' directory is in your PATH."
    # The script will continue so 'vse' is still installed.
}

# ---  Install VS Code Extension ---
Write-Host "Attempting to install VS Code extension..."
try {
    $VsixFile = (Get-ChildItem -Path $InstallDir -Filter "*.vsix" | Select-Object -First 1).FullName
    if ($VsixFile) {
        Write-Host "Found VS Code. Installing extension..."
        # The '&' is the call operator in PowerShell, needed to run commands with arguments
        & code --install-extension $VsixFile
    } else {
        Write-Warning ".vsix file not found in downloaded package."
    }
} catch {
    $VsixFileName = (Get-ChildItem -Path $InstallDir -Filter "*.vsix" | Select-Object -First 1).Name
    Write-Host ""
    Write-Warning "VS Code command-line tool ('code') not found or installation failed."
    Write-Warning "To install the extension, open VS Code, go to the Extensions view, click the '...' menu,"
    Write-Warning "select 'Install from VSIX...', and choose the file: $InstallDir\$VsixFileName"
}

# --- Cleanup ---
Remove-Item -Recurse -Force $TempDir

Write-Host ""
Write-Host "✅ Installation complete!"
Write-Host "IMPORTANT: You must open a new terminal for all changes to take effect."