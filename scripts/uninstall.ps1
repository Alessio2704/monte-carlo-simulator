$ErrorActionPreference = 'Stop'

Write-Host "Welcome to the ValuaScript Uninstaller for Windows!"

# --- Configuration ---
$InstallDir = [System.Environment]::GetFolderPath('MyDocuments') + "\ValuaScript-Tools"

# --- Remove vse from PATH ---
Write-Host "Removing ValuaScript engine from your PATH..."
$UserPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
$PathParts = $UserPath -split ';' | Where-Object { $_ -ne $InstallDir -and $_ }
$NewPath = $PathParts -join ';'
if ($NewPath -ne $UserPath) {
    [System.Environment]::SetEnvironmentVariable('Path', $NewPath, 'User')
    Write-Host "✅ 'vse' has been removed from your PATH."
} else {
    Write-Host "ValuaScript directory not found in PATH, skipping."
}


# --- Uninstall vsc from pipx ---
try {
    Get-Command pipx -ErrorAction SilentlyContinue | Out-Null
    Write-Host "Uninstalling the vsc compiler..."
    pipx uninstall valuascript-compiler
} catch {
    Write-Host "pipx or valuascript-compiler not found, skipping compiler uninstallation."
}

# --- Remove Installation Directory ---
if (Test-Path $InstallDir) {
    Write-Host "Removing installation directory: $InstallDir"
    Remove-Item -Recurse -Force $InstallDir
} else {
    Write-Host "Installation directory not found, skipping."
}

# --- Uninstall VS Code Extension ---
$ExtensionId = "AlessioMarcuzzi.valuascript-language"
$CodeCmd = Get-Command code -ErrorAction SilentlyContinue
if ($CodeCmd) {
    Write-Host "Uninstalling VS Code extension: $ExtensionId..."
    try {
        & $CodeCmd.Source --uninstall-extension $ExtensionId
    } catch {}
}

Write-Host ""
Write-Host "✅ Uninstallation complete!"
Write-Host "IMPORTANT: You must open a new terminal for the PATH changes to take effect."