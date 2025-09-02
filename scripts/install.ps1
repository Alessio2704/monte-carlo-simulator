$ErrorActionPreference = 'Stop'

Write-Host "Welcome to the ValuaScript Installer for Windows!"

# --- Configuration ---
$Repo = "Alessio2704/monte-carlo-simulator"
$InstallDir = [System.Environment]::GetFolderPath('MyDocuments') + "\ValuaScript-Tools"

# --- Detect Architecture ---
$AssetSuffix = ""
Write-Host "Detecting system architecture..."
switch ($env:PROCESSOR_ARCHITECTURE) {
    "AMD64" {
        $AssetSuffix = "windows-x64"
    }
    "ARM64" {
        $AssetSuffix = "windows-arm64"
    }
    default {
        Write-Error "Error: Unsupported Windows architecture '$($env:PROCESSOR_ARCHITECTURE)'."
        exit 1
    }
}
Write-Host "Detected architecture: $($env:PROCESSOR_ARCHITECTURE). Using asset suffix: $AssetSuffix"


# --- Fetch Latest Release ---
Write-Host "Fetching latest release..."
$LatestReleaseApiUrl = "https://api.github.com/repos/$Repo/releases/latest"
$Assets = (Invoke-RestMethod -Uri $LatestReleaseApiUrl).assets
$DownloadUrlEngine = ($Assets | Where-Object { $_.name -like "*$AssetSuffix.zip" }).browser_download_url
$DownloadUrlVsix = ($Assets | Where-Object { $_.name -like "*.vsix" }).browser_download_url
$VsixName = ($Assets | Where-Object { $_.name -like "*.vsix" }).name

if (-not $DownloadUrlEngine) { Write-Error "Error: Could not find engine release for your system ($AssetSuffix)."; exit 1 }

# --- Download and Install vse ---
Write-Host "Downloading ValuaScript engine from: $DownloadUrlEngine"
if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
New-Item -ItemType Directory -Path $InstallDir | Out-Null
$TempZip = Join-Path $env:TEMP "valuascript.zip"
Invoke-WebRequest -Uri $DownloadUrlEngine -OutFile $TempZip
Expand-Archive -Path $TempZip -DestinationPath $InstallDir
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
    # Ensure Python is available
    Get-Command python | Out-Null
    
    Write-Host "Installing/upgrading pipx..."
    python -m pip install --user -q --upgrade pipx
    
    # Find the Python user 'Scripts' directory and add it to this script's PATH.
    # This makes the 'pipx' command available immediately for the next steps.
    Write-Host "Making pipx available to the current session..."
    $PythonUserScripts = Join-Path -Path ([System.Environment]::GetFolderPath('ApplicationData')) -ChildPath 'Python'
    if (Test-Path $PythonUserScripts) {
        $PythonVersionFolder = Get-ChildItem -Path $PythonUserScripts -Directory | Select-Object -Last 1
        if ($PythonVersionFolder) {
            $FullScriptsPath = Join-Path -Path $PythonVersionFolder.FullName -ChildPath 'Scripts'
            if (Test-Path $FullScriptsPath) {
                $env:Path += ";$FullScriptsPath"
                Write-Host "Temporarily added $FullScriptsPath to this session's PATH."
            }
        }
    }
    
    Write-Host "Ensuring pipx is in the PATH for future sessions..."
    # We still run ensurepath to make the change permanent for the user.
    python -m pipx ensurepath
    
    Write-Host "Installing valuascript-compiler with pipx..."
    # Now this command will work because pipx.exe is found in the session's PATH.
    pipx install valuascript-compiler

} catch {
    Write-Host ""
    Write-Host "❌ Error: Failed to install the 'vsc' compiler."
    Write-Host "Please ensure Python 3 is installed and its 'Scripts' directory is added to PATH."
}


# --- Install VS Code Extension ---
if (-not $DownloadUrlVsix) {
    Write-Host "Warning: Could not find a .vsix extension file in the release. Skipping."
} else {
    Write-Host "Attempting to install the ValuaScript VS Code extension..."
    $CodeCmd = Get-Command code -ErrorAction SilentlyContinue
    if (-not $CodeCmd) {
        Write-Host "Warning: VS Code command-line tool ('code') not found in PATH."
        Write-Host "You can install it manually from the VS Code Command Palette (search for 'Shell Command: Install')."
    } else {
        Write-Host "Found VS Code. Downloading and installing extension..."
        $VsixPath = Join-Path $InstallDir $VsixName
        Invoke-WebRequest -Uri $DownloadUrlVsix -OutFile $VsixPath
        
        try {
            & $CodeCmd.Source --install-extension $VsixPath
            Write-Host "✅ VS Code extension installed."
        } catch {
            Write-Host "Warning: Failed to install VS Code extension. Is VS Code closed?"
        }
    }
}


# --- Cleanup ---
Remove-Item -Force $TempZip

Write-Host ""
Write-Host "✅ Installation complete!"
Write-Host "IMPORTANT: You must open a new terminal for all changes to take effect."